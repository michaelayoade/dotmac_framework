/**
 * Payment Management - Focused component for payment operations
 * Handles payment transaction viewing and management
 */

'use client';

import { CreditCardIcon } from 'lucide-react';
import { StatusBadge } from '@dotmac/providers/indicators/StatusIndicators';
import type { Payment } from '../../../types/billing';

interface PaymentManagementProps {
  payments: Payment[];
  onPaymentAction?: (action: string, paymentId: string) => void;
}

export function PaymentManagement({ payments, onPaymentAction }: PaymentManagementProps) {
  return (
    <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
      <div className='p-6 border-b border-gray-200'>
        <h3 className='text-lg font-semibold text-gray-900'>Payment Transactions</h3>
        <p className='text-sm text-gray-500'>Track and manage all payment transactions</p>
      </div>

      <div className='overflow-x-auto'>
        <table className='min-w-full divide-y divide-gray-200'>
          <thead className='bg-gray-50'>
            <tr>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Payment
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Customer
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Amount
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Method
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Status
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Date
              </th>
            </tr>
          </thead>
          <tbody className='bg-white divide-y divide-gray-200'>
            {payments.map((payment) => (
              <PaymentRow key={payment.id} payment={payment} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface PaymentRowProps {
  payment: Payment;
}

function PaymentRow({ payment }: PaymentRowProps) {
  return (
    <tr className='hover:bg-gray-50'>
      <td className='px-6 py-4'>
        <div className='flex items-center space-x-3'>
          <div className='flex-shrink-0'>
            <CreditCardIcon className='w-5 h-5 text-gray-400' />
          </div>
          <div>
            <div className='text-sm font-medium text-gray-900'>{payment.id}</div>
            <div className='text-sm text-gray-500'>{payment.transactionId}</div>
          </div>
        </div>
      </td>
      <td className='px-6 py-4'>
        <div className='text-sm font-medium text-gray-900'>{payment.customerName}</div>
        <div className='text-sm text-gray-500'>
          {payment.invoiceId ? `Invoice: ${payment.invoiceId}` : 'Standalone Payment'}
        </div>
      </td>
      <td className='px-6 py-4'>
        <div className='text-sm text-gray-900'>${payment.amount.toFixed(2)}</div>
        <div className='text-xs text-gray-500'>
          Fees: ${(payment.fees.processing + payment.fees.gateway).toFixed(2)}
        </div>
      </td>
      <td className='px-6 py-4'>
        <div className='text-sm text-gray-900 capitalize'>{payment.method.replace('_', ' ')}</div>
        <div className='text-xs text-gray-500'>{payment.gateway}</div>
      </td>
      <td className='px-6 py-4'>
        <StatusBadge
          variant={
            payment.status === 'completed'
              ? 'paid'
              : payment.status === 'pending'
                ? 'processing'
                : payment.status === 'failed'
                  ? 'overdue'
                  : 'suspended'
          }
          size='sm'
          showDot={true}
          pulse={payment.status === 'pending'}
        >
          {payment.status}
        </StatusBadge>
      </td>
      <td className='px-6 py-4'>
        <div className='text-sm text-gray-900'>
          {payment.processedAt ? new Date(payment.processedAt).toLocaleDateString() : 'Pending'}
        </div>
      </td>
    </tr>
  );
}
