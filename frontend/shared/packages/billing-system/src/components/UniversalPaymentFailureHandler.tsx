'use client';

import React, { useState, useCallback, useEffect } from 'react';
import {
  AlertTriangle,
  RefreshCw,
  CreditCard,
  Mail,
  Phone,
  Clock,
  CheckCircle,
  XCircle,
  Info,
  ExternalLink,
  Bell,
  Users,
} from 'lucide-react';
import { cn, formatCurrency, formatDate, getErrorMessage, debounce } from '../utils';
import type { Payment, PaymentMethod, Invoice } from '../types';

interface FailedPayment extends Payment {
  failureReason?: string;
  retryCount?: number;
  nextRetryDate?: Date;
  invoice?: Invoice;
}

interface UniversalPaymentFailureHandlerProps {
  failedPayments: FailedPayment[];
  onRetryPayment: (paymentId: string, paymentMethodId?: string) => Promise<void>;
  onUpdatePaymentMethod: (paymentId: string) => void;
  onContactCustomer: (paymentId: string, method: 'email' | 'phone') => Promise<void>;
  onSuspendService: (paymentId: string) => Promise<void>;
  onWaivePayment: (paymentId: string, reason: string) => Promise<void>;
  paymentMethods?: PaymentMethod[];
  portalType?: 'admin' | 'customer' | 'reseller' | 'management';
  autoRetryEnabled?: boolean;
  maxRetryAttempts?: number;
  currency?: string;
  className?: string;
}

interface RetryStrategy {
  id: string;
  name: string;
  description: string;
  immediate: boolean;
  delay?: number; // in minutes
  requiresUserAction?: boolean;
}

const RETRY_STRATEGIES: RetryStrategy[] = [
  {
    id: 'immediate',
    name: 'Retry Now',
    description: 'Attempt payment immediately with the same method',
    immediate: true,
  },
  {
    id: 'delayed',
    name: 'Retry in 1 Hour',
    description: 'Schedule retry in 1 hour (good for temporary card issues)',
    immediate: false,
    delay: 60,
  },
  {
    id: 'daily',
    name: 'Daily Retry',
    description: 'Retry once daily for 3 days',
    immediate: false,
    delay: 1440, // 24 hours
  },
  {
    id: 'update_method',
    name: 'Update Payment Method',
    description: 'Request customer to update their payment method',
    immediate: false,
    requiresUserAction: true,
  },
];

export function UniversalPaymentFailureHandler({
  failedPayments,
  onRetryPayment,
  onUpdatePaymentMethod,
  onContactCustomer,
  onSuspendService,
  onWaivePayment,
  paymentMethods = [],
  portalType = 'admin',
  autoRetryEnabled = false,
  maxRetryAttempts = 3,
  currency = 'USD',
  className,
}: UniversalPaymentFailureHandlerProps) {
  const [processingPayments, setProcessingPayments] = useState<Set<string>>(new Set());
  const [selectedPayments, setSelectedPayments] = useState<Set<string>>(new Set());
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('immediate');
  const [contactingCustomers, setContactingCustomers] = useState<Set<string>>(new Set());
  const [showWaiveModal, setShowWaiveModal] = useState<string | null>(null);
  const [waiveReason, setWaiveReason] = useState('');

  const getFailureCategory = (reason: string) => {
    const lowerReason = reason.toLowerCase();
    if (lowerReason.includes('insufficient') || lowerReason.includes('declined')) {
      return 'insufficient_funds';
    }
    if (lowerReason.includes('expired') || lowerReason.includes('invalid')) {
      return 'invalid_card';
    }
    if (lowerReason.includes('fraud') || lowerReason.includes('suspicious')) {
      return 'fraud_prevention';
    }
    if (lowerReason.includes('limit') || lowerReason.includes('exceeded')) {
      return 'limit_exceeded';
    }
    return 'other';
  };

  const getFailureSeverity = (payment: FailedPayment) => {
    const retryCount = payment.retryCount || 0;
    const daysSinceFailed = payment.processedAt
      ? Math.floor((Date.now() - new Date(payment.processedAt).getTime()) / (1000 * 60 * 60 * 24))
      : 0;

    if (retryCount >= maxRetryAttempts || daysSinceFailed >= 7) return 'critical';
    if (retryCount >= 2 || daysSinceFailed >= 3) return 'high';
    if (retryCount >= 1 || daysSinceFailed >= 1) return 'medium';
    return 'low';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'high':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  const getRecommendedActions = (payment: FailedPayment) => {
    const category = getFailureCategory(payment.failureReason || '');
    const severity = getFailureSeverity(payment);
    const retryCount = payment.retryCount || 0;

    const actions = [];

    if (category === 'insufficient_funds' && retryCount < 2) {
      actions.push({ type: 'retry', priority: 'high', text: 'Retry in 24 hours' });
      actions.push({
        type: 'contact',
        priority: 'medium',
        text: 'Contact customer about low balance',
      });
    } else if (category === 'invalid_card') {
      actions.push({
        type: 'update_method',
        priority: 'high',
        text: 'Request payment method update',
      });
      actions.push({ type: 'contact', priority: 'high', text: 'Contact customer immediately' });
    } else if (category === 'fraud_prevention') {
      actions.push({ type: 'contact', priority: 'high', text: 'Verify transaction with customer' });
      actions.push({
        type: 'manual_retry',
        priority: 'medium',
        text: 'Manual retry after verification',
      });
    } else if (severity === 'critical') {
      actions.push({ type: 'suspend', priority: 'high', text: 'Consider service suspension' });
      actions.push({ type: 'escalate', priority: 'high', text: 'Escalate to collections' });
    }

    return actions;
  };

  const handleRetryPayment = useCallback(
    async (paymentId: string, strategy: string, paymentMethodId?: string) => {
      setProcessingPayments((prev) => new Set([...prev, paymentId]));

      try {
        await onRetryPayment(paymentId, paymentMethodId);

        // Remove from selected payments if successful
        setSelectedPayments((prev) => {
          const newSet = new Set(prev);
          newSet.delete(paymentId);
          return newSet;
        });
      } catch (error) {
        console.error('Failed to retry payment:', error);
      } finally {
        setProcessingPayments((prev) => {
          const newSet = new Set(prev);
          newSet.delete(paymentId);
          return newSet;
        });
      }
    },
    [onRetryPayment]
  );

  const handleBulkAction = useCallback(
    async (action: string) => {
      const paymentIds = Array.from(selectedPayments);

      for (const paymentId of paymentIds) {
        try {
          switch (action) {
            case 'retry':
              await handleRetryPayment(paymentId, selectedStrategy);
              break;
            case 'contact_email':
              await onContactCustomer(paymentId, 'email');
              break;
            case 'contact_phone':
              await onContactCustomer(paymentId, 'phone');
              break;
          }
        } catch (error) {
          console.error(`Failed bulk action ${action} for payment ${paymentId}:`, error);
        }
      }

      setSelectedPayments(new Set());
      setShowBulkActions(false);
    },
    [selectedPayments, selectedStrategy, handleRetryPayment, onContactCustomer]
  );

  const handleContactCustomer = useCallback(
    async (paymentId: string, method: 'email' | 'phone') => {
      setContactingCustomers((prev) => new Set([...prev, paymentId]));

      try {
        await onContactCustomer(paymentId, method);
      } catch (error) {
        console.error('Failed to contact customer:', error);
      } finally {
        setContactingCustomers((prev) => {
          const newSet = new Set(prev);
          newSet.delete(paymentId);
          return newSet;
        });
      }
    },
    [onContactCustomer]
  );

  const handleWaivePayment = useCallback(async () => {
    if (!showWaiveModal || !waiveReason.trim()) return;

    try {
      await onWaivePayment(showWaiveModal, waiveReason);
      setShowWaiveModal(null);
      setWaiveReason('');
    } catch (error) {
      console.error('Failed to waive payment:', error);
    }
  }, [showWaiveModal, waiveReason, onWaivePayment]);

  // Group payments by severity and category
  const groupedPayments = failedPayments.reduce(
    (groups, payment) => {
      const severity = getFailureSeverity(payment);
      const category = getFailureCategory(payment.failureReason || '');

      if (!groups[severity]) groups[severity] = {};
      if (!groups[severity][category]) groups[severity][category] = [];

      groups[severity][category].push(payment);
      return groups;
    },
    {} as Record<string, Record<string, FailedPayment[]>>
  );

  const totalFailedAmount = failedPayments.reduce((sum, payment) => sum + payment.amount, 0);
  const avgRetryCount =
    failedPayments.length > 0
      ? failedPayments.reduce((sum, p) => sum + (p.retryCount || 0), 0) / failedPayments.length
      : 0;

  const renderSummaryCards = () => (
    <div className='grid grid-cols-1 md:grid-cols-4 gap-4 mb-6'>
      <div className='bg-white rounded-lg border border-red-200 p-4'>
        <div className='flex items-center justify-between'>
          <div>
            <p className='text-sm font-medium text-gray-600'>Failed Payments</p>
            <p className='text-2xl font-bold text-red-600'>{failedPayments.length}</p>
            <p className='text-sm text-gray-500'>{formatCurrency(totalFailedAmount, currency)}</p>
          </div>
          <XCircle className='w-8 h-8 text-red-600' />
        </div>
      </div>

      <div className='bg-white rounded-lg border border-orange-200 p-4'>
        <div className='flex items-center justify-between'>
          <div>
            <p className='text-sm font-medium text-gray-600'>Avg Retry Count</p>
            <p className='text-2xl font-bold text-orange-600'>{avgRetryCount.toFixed(1)}</p>
            <p className='text-sm text-gray-500'>Per payment</p>
          </div>
          <RefreshCw className='w-8 h-8 text-orange-600' />
        </div>
      </div>

      <div className='bg-white rounded-lg border border-yellow-200 p-4'>
        <div className='flex items-center justify-between'>
          <div>
            <p className='text-sm font-medium text-gray-600'>Need Action</p>
            <p className='text-2xl font-bold text-yellow-600'>
              {failedPayments.filter((p) => getFailureSeverity(p) === 'critical').length}
            </p>
            <p className='text-sm text-gray-500'>Critical failures</p>
          </div>
          <AlertTriangle className='w-8 h-8 text-yellow-600' />
        </div>
      </div>

      <div className='bg-white rounded-lg border border-blue-200 p-4'>
        <div className='flex items-center justify-between'>
          <div>
            <p className='text-sm font-medium text-gray-600'>Auto Retry</p>
            <p className='text-2xl font-bold text-blue-600'>{autoRetryEnabled ? 'ON' : 'OFF'}</p>
            <p className='text-sm text-gray-500'>Max {maxRetryAttempts} attempts</p>
          </div>
          <Clock className='w-8 h-8 text-blue-600' />
        </div>
      </div>
    </div>
  );

  const renderBulkActions = () =>
    selectedPayments.size > 0 && (
      <div className='bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6'>
        <div className='flex items-center justify-between'>
          <div className='flex items-center space-x-4'>
            <span className='text-sm font-medium text-blue-900'>
              {selectedPayments.size} payments selected
            </span>
            <select
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className='border border-blue-300 rounded px-3 py-1 text-sm'
            >
              {RETRY_STRATEGIES.map((strategy) => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name}
                </option>
              ))}
            </select>
          </div>
          <div className='flex items-center space-x-2'>
            <button
              onClick={() => handleBulkAction('retry')}
              className='px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm'
            >
              Retry Selected
            </button>
            <button
              onClick={() => handleBulkAction('contact_email')}
              className='px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm'
            >
              Email Customers
            </button>
            <button
              onClick={() => setSelectedPayments(new Set())}
              className='px-3 py-1 border border-gray-300 text-gray-700 rounded hover:bg-gray-50 text-sm'
            >
              Clear Selection
            </button>
          </div>
        </div>
      </div>
    );

  const renderWaiveModal = () =>
    showWaiveModal && (
      <div className='fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50'>
        <div className='bg-white rounded-lg p-6 max-w-md w-full mx-4'>
          <h3 className='text-lg font-medium text-gray-900 mb-4'>Waive Payment</h3>
          <div className='space-y-4'>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                Reason for waiving payment
              </label>
              <textarea
                value={waiveReason}
                onChange={(e) => setWaiveReason(e.target.value)}
                rows={3}
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                placeholder='Provide a reason for waiving this payment...'
              />
            </div>
            <div className='flex justify-end space-x-3'>
              <button
                onClick={() => {
                  setShowWaiveModal(null);
                  setWaiveReason('');
                }}
                className='px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50'
              >
                Cancel
              </button>
              <button
                onClick={handleWaivePayment}
                disabled={!waiveReason.trim()}
                className='px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed'
              >
                Waive Payment
              </button>
            </div>
          </div>
        </div>
      </div>
    );

  if (failedPayments.length === 0) {
    return (
      <div className={cn('bg-white rounded-lg border border-gray-200 p-8 text-center', className)}>
        <CheckCircle className='w-12 h-12 text-green-600 mx-auto mb-4' />
        <h3 className='text-lg font-medium text-gray-900 mb-2'>No Failed Payments</h3>
        <p className='text-gray-500'>All payments are processing successfully.</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      <div className='flex items-center justify-between'>
        <h2 className='text-xl font-semibold text-gray-900'>Payment Failure Management</h2>
        <div className='flex items-center space-x-2'>
          <button
            onClick={() => setShowBulkActions(!showBulkActions)}
            className='flex items-center px-3 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm'
          >
            <Users className='w-4 h-4 mr-2' />
            Bulk Actions
          </button>
        </div>
      </div>

      {renderSummaryCards()}
      {renderBulkActions()}

      <div className='space-y-6'>
        {Object.entries(groupedPayments).map(([severity, categories]) => (
          <div key={severity} className='space-y-4'>
            <h3
              className={cn(
                'text-lg font-medium capitalize px-3 py-1 rounded inline-block',
                getSeverityColor(severity)
              )}
            >
              {severity} Priority ({Object.values(categories).flat().length})
            </h3>

            {Object.entries(categories).map(([category, payments]) => (
              <div
                key={category}
                className='bg-white border border-gray-200 rounded-lg overflow-hidden'
              >
                <div className='px-4 py-3 border-b border-gray-200 bg-gray-50'>
                  <h4 className='font-medium text-gray-900 capitalize'>
                    {category.replace('_', ' ')} ({payments.length})
                  </h4>
                </div>

                <div className='overflow-x-auto'>
                  <table className='min-w-full divide-y divide-gray-200'>
                    <thead className='bg-gray-50'>
                      <tr>
                        <th className='px-4 py-3 text-left'>
                          <input
                            type='checkbox'
                            checked={payments.every((p) => selectedPayments.has(p.id))}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedPayments(
                                  (prev) => new Set([...prev, ...payments.map((p) => p.id)])
                                );
                              } else {
                                setSelectedPayments((prev) => {
                                  const newSet = new Set(prev);
                                  payments.forEach((p) => newSet.delete(p.id));
                                  return newSet;
                                });
                              }
                            }}
                            className='rounded border-gray-300'
                          />
                        </th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase'>
                          Payment
                        </th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase'>
                          Customer
                        </th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase'>
                          Amount
                        </th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase'>
                          Failure Reason
                        </th>
                        <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase'>
                          Retries
                        </th>
                        <th className='px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase'>
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className='bg-white divide-y divide-gray-200'>
                      {payments.map((payment) => {
                        const recommendations = getRecommendedActions(payment);
                        const isProcessing = processingPayments.has(payment.id);
                        const isContacting = contactingCustomers.has(payment.id);

                        return (
                          <tr key={payment.id} className='hover:bg-gray-50'>
                            <td className='px-4 py-3'>
                              <input
                                type='checkbox'
                                checked={selectedPayments.has(payment.id)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedPayments((prev) => new Set([...prev, payment.id]));
                                  } else {
                                    setSelectedPayments((prev) => {
                                      const newSet = new Set(prev);
                                      newSet.delete(payment.id);
                                      return newSet;
                                    });
                                  }
                                }}
                                className='rounded border-gray-300'
                              />
                            </td>
                            <td className='px-4 py-3'>
                              <div>
                                <div className='text-sm font-medium text-gray-900'>
                                  {payment.id}
                                </div>
                                <div className='text-sm text-gray-500'>
                                  {formatDate(payment.createdAt)}
                                </div>
                              </div>
                            </td>
                            <td className='px-4 py-3'>
                              <div className='text-sm text-gray-900'>{payment.customerName}</div>
                            </td>
                            <td className='px-4 py-3 text-sm font-medium text-gray-900'>
                              {formatCurrency(payment.amount, currency)}
                            </td>
                            <td className='px-4 py-3'>
                              <div className='text-sm text-red-600'>
                                {payment.failureReason || 'Unknown error'}
                              </div>
                            </td>
                            <td className='px-4 py-3'>
                              <div className='flex items-center'>
                                <span className='text-sm text-gray-900'>
                                  {payment.retryCount || 0}/{maxRetryAttempts}
                                </span>
                                {payment.nextRetryDate && (
                                  <Clock className='w-4 h-4 text-gray-400 ml-2' />
                                )}
                              </div>
                            </td>
                            <td className='px-4 py-3 text-right'>
                              <div className='flex items-center justify-end space-x-2'>
                                <button
                                  onClick={() => handleRetryPayment(payment.id, 'immediate')}
                                  disabled={isProcessing}
                                  className='flex items-center px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50'
                                  title='Retry Payment'
                                >
                                  {isProcessing ? (
                                    <div className='animate-spin rounded-full h-3 w-3 border border-white border-t-transparent mr-1' />
                                  ) : (
                                    <RefreshCw className='w-3 h-3 mr-1' />
                                  )}
                                  Retry
                                </button>

                                <button
                                  onClick={() => handleContactCustomer(payment.id, 'email')}
                                  disabled={isContacting}
                                  className='p-1 text-green-600 hover:bg-green-50 rounded'
                                  title='Email Customer'
                                >
                                  {isContacting ? (
                                    <div className='animate-spin rounded-full h-3 w-3 border border-green-600 border-t-transparent' />
                                  ) : (
                                    <Mail className='w-3 h-3' />
                                  )}
                                </button>

                                <button
                                  onClick={() => onUpdatePaymentMethod(payment.id)}
                                  className='p-1 text-orange-600 hover:bg-orange-50 rounded'
                                  title='Update Payment Method'
                                >
                                  <CreditCard className='w-3 h-3' />
                                </button>

                                {portalType === 'admin' && (
                                  <>
                                    <button
                                      onClick={() => onSuspendService(payment.id)}
                                      className='p-1 text-red-600 hover:bg-red-50 rounded'
                                      title='Suspend Service'
                                    >
                                      <XCircle className='w-3 h-3' />
                                    </button>
                                    <button
                                      onClick={() => setShowWaiveModal(payment.id)}
                                      className='p-1 text-purple-600 hover:bg-purple-50 rounded'
                                      title='Waive Payment'
                                    >
                                      <CheckCircle className='w-3 h-3' />
                                    </button>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>

      {renderWaiveModal()}
    </div>
  );
}
