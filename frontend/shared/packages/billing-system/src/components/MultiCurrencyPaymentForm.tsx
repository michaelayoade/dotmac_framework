/**
 * Multi-Currency Payment Form with Manual Exchange Rate Entry
 *
 * Allows customers to pay in different currencies with manual exchange rate setting.
 * Uses DRY patterns from the unified currency formatting system.
 */

import React, { useState, useEffect } from 'react';
import {
  formatCurrency,
  getSupportedCurrencies,
  type SupportedCurrency,
} from '@dotmac/utils/formatting';

interface CustomerCurrency {
  id: string;
  currency_code: string;
  is_base_currency: boolean;
  display_name: string | null;
  is_active: boolean;
}

interface ExchangeRate {
  id: string;
  from_currency: string;
  to_currency: string;
  exchange_rate: number;
  rate_date: string;
  source: string | null;
}

interface MultiCurrencyPaymentFormProps {
  customerId: string;
  invoiceId?: string;
  invoiceAmount?: number;
  invoiceCurrency?: string;
  onPaymentSubmit: (paymentData: PaymentWithExchangeRate) => Promise<void>;
  onCancel?: () => void;
}

interface PaymentWithExchangeRate {
  customer_id: string;
  invoice_id?: string;
  payment_amount: number;
  payment_currency: string;
  payment_method: string;
  payment_notes?: string;
  base_currency: string;
  exchange_rate: number;
  rate_source?: string;
  rate_notes?: string;
}

export const MultiCurrencyPaymentForm: React.FC<MultiCurrencyPaymentFormProps> = ({
  customerId,
  invoiceId,
  invoiceAmount,
  invoiceCurrency,
  onPaymentSubmit,
  onCancel,
}) => {
  // State management
  const [customerCurrencies, setCustomerCurrencies] = useState<CustomerCurrency[]>([]);
  const [baseCurrency, setBaseCurrency] = useState<string>('');
  const [paymentCurrency, setPaymentCurrency] = useState<string>(invoiceCurrency || 'USD');
  const [paymentAmount, setPaymentAmount] = useState<string>(invoiceAmount?.toString() || '');
  const [exchangeRate, setExchangeRate] = useState<string>('1.00');
  const [paymentMethod, setPaymentMethod] = useState<string>('credit_card');
  const [paymentNotes, setPaymentNotes] = useState<string>('');
  const [rateSource, setRateSource] = useState<string>('Manual Entry');
  const [rateNotes, setRateNotes] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Calculated values
  const convertedAmount =
    paymentCurrency === baseCurrency
      ? parseFloat(paymentAmount || '0')
      : parseFloat(paymentAmount || '0') * parseFloat(exchangeRate || '1');

  // Load customer currencies on mount
  useEffect(() => {
    loadCustomerCurrencies();
  }, [customerId]);

  // Auto-set exchange rate to 1.0 if same currency
  useEffect(() => {
    if (paymentCurrency === baseCurrency) {
      setExchangeRate('1.00');
    }
  }, [paymentCurrency, baseCurrency]);

  const loadCustomerCurrencies = async () => {
    try {
      const response = await fetch(`/api/customers/${customerId}/currencies`);
      const data = await response.json();

      setCustomerCurrencies(data.currencies || []);

      // Find base currency
      const base = data.currencies.find((c: CustomerCurrency) => c.is_base_currency);
      if (base) {
        setBaseCurrency(base.currency_code);
      }
    } catch (error) {
      console.error('Failed to load customer currencies:', error);
      setErrors({ general: 'Failed to load currency settings' });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!paymentAmount || parseFloat(paymentAmount) <= 0) {
      newErrors.paymentAmount = 'Payment amount is required and must be positive';
    }

    if (!paymentCurrency) {
      newErrors.paymentCurrency = 'Payment currency is required';
    }

    if (!exchangeRate || parseFloat(exchangeRate) <= 0) {
      newErrors.exchangeRate = 'Exchange rate is required and must be positive';
    }

    if (parseFloat(exchangeRate) > 1000000) {
      newErrors.exchangeRate = 'Exchange rate seems unreasonably high';
    }

    if (!paymentMethod) {
      newErrors.paymentMethod = 'Payment method is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      const paymentData: PaymentWithExchangeRate = {
        customer_id: customerId,
        invoice_id: invoiceId,
        payment_amount: parseFloat(paymentAmount),
        payment_currency: paymentCurrency,
        payment_method: paymentMethod,
        payment_notes: paymentNotes || undefined,
        base_currency: baseCurrency,
        exchange_rate: parseFloat(exchangeRate),
        rate_source: rateSource || undefined,
        rate_notes: rateNotes || undefined,
      };

      await onPaymentSubmit(paymentData);
    } catch (error: any) {
      setErrors({
        general: error.message || 'Payment processing failed',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const supportedCurrencies = getSupportedCurrencies();
  const activeCurrencies = customerCurrencies.filter((c) => c.is_active);

  return (
    <div className='max-w-2xl mx-auto bg-white rounded-lg shadow-md p-6'>
      <div className='mb-6'>
        <h2 className='text-2xl font-bold text-gray-900'>Multi-Currency Payment</h2>
        <p className='text-gray-600 mt-2'>
          Process payment in different currency with manual exchange rate
        </p>
      </div>

      {errors.general && (
        <div className='mb-6 p-4 bg-red-50 border border-red-200 rounded-md'>
          <div className='text-red-800'>{errors.general}</div>
        </div>
      )}

      <form onSubmit={handleSubmit} className='space-y-6'>
        {/* Currency Information */}
        <div className='bg-blue-50 border border-blue-200 rounded-md p-4'>
          <h3 className='font-semibold text-blue-900 mb-2'>Currency Information</h3>
          <div className='grid grid-cols-2 gap-4 text-sm'>
            <div>
              <span className='font-medium'>Base Currency:</span>
              <span className='ml-2'>{baseCurrency || 'Not set'}</span>
            </div>
            <div>
              <span className='font-medium'>Available Currencies:</span>
              <span className='ml-2'>
                {activeCurrencies.map((c) => c.currency_code).join(', ') || 'None configured'}
              </span>
            </div>
          </div>
        </div>

        {/* Payment Amount */}
        <div>
          <label className='block text-sm font-medium text-gray-700 mb-2'>Payment Amount</label>
          <div className='flex gap-4'>
            <div className='flex-1'>
              <input
                type='number'
                step='0.01'
                min='0'
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
                placeholder='Enter payment amount'
                className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.paymentAmount ? 'border-red-300' : 'border-gray-300'
                }`}
              />
              {errors.paymentAmount && (
                <p className='text-red-600 text-xs mt-1'>{errors.paymentAmount}</p>
              )}
            </div>
            <div className='w-32'>
              <select
                value={paymentCurrency}
                onChange={(e) => setPaymentCurrency(e.target.value)}
                className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.paymentCurrency ? 'border-red-300' : 'border-gray-300'
                }`}
              >
                {supportedCurrencies.map((currency) => (
                  <option key={currency} value={currency}>
                    {currency}
                  </option>
                ))}
              </select>
              {errors.paymentCurrency && (
                <p className='text-red-600 text-xs mt-1'>{errors.paymentCurrency}</p>
              )}
            </div>
          </div>
        </div>

        {/* Exchange Rate */}
        {paymentCurrency !== baseCurrency && (
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-2'>
              Exchange Rate ({paymentCurrency} to {baseCurrency})
            </label>
            <div className='flex gap-4'>
              <div className='flex-1'>
                <input
                  type='number'
                  step='0.000001'
                  min='0'
                  value={exchangeRate}
                  onChange={(e) => setExchangeRate(e.target.value)}
                  placeholder='Enter exchange rate'
                  className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.exchangeRate ? 'border-red-300' : 'border-gray-300'
                  }`}
                />
                {errors.exchangeRate && (
                  <p className='text-red-600 text-xs mt-1'>{errors.exchangeRate}</p>
                )}
              </div>
              <div className='w-40'>
                <input
                  type='text'
                  value={rateSource}
                  onChange={(e) => setRateSource(e.target.value)}
                  placeholder='Rate source'
                  className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
                />
              </div>
            </div>
            <p className='text-xs text-gray-500 mt-1'>
              1 {paymentCurrency} = {exchangeRate} {baseCurrency}
            </p>
          </div>
        )}

        {/* Conversion Preview */}
        {paymentAmount && exchangeRate && (
          <div className='bg-gray-50 border border-gray-200 rounded-md p-4'>
            <h3 className='font-semibold text-gray-900 mb-2'>Conversion Preview</h3>
            <div className='space-y-2 text-sm'>
              <div className='flex justify-between'>
                <span>Payment Amount:</span>
                <span className='font-medium'>
                  {formatCurrency(parseFloat(paymentAmount), {
                    currency: paymentCurrency as SupportedCurrency,
                  })}
                </span>
              </div>
              <div className='flex justify-between'>
                <span>Exchange Rate:</span>
                <span className='font-medium'>
                  1 {paymentCurrency} = {exchangeRate} {baseCurrency}
                </span>
              </div>
              <div className='flex justify-between border-t pt-2'>
                <span className='font-semibold'>Converted Amount:</span>
                <span className='font-semibold text-blue-600'>
                  {formatCurrency(convertedAmount, { currency: baseCurrency as SupportedCurrency })}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Payment Method */}
        <div>
          <label className='block text-sm font-medium text-gray-700 mb-2'>Payment Method</label>
          <select
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.paymentMethod ? 'border-red-300' : 'border-gray-300'
            }`}
          >
            <option value='credit_card'>Credit Card</option>
            <option value='debit_card'>Debit Card</option>
            <option value='bank_transfer'>Bank Transfer</option>
            <option value='cash'>Cash</option>
            <option value='check'>Check</option>
          </select>
          {errors.paymentMethod && (
            <p className='text-red-600 text-xs mt-1'>{errors.paymentMethod}</p>
          )}
        </div>

        {/* Payment Notes */}
        <div>
          <label className='block text-sm font-medium text-gray-700 mb-2'>
            Payment Notes (Optional)
          </label>
          <textarea
            value={paymentNotes}
            onChange={(e) => setPaymentNotes(e.target.value)}
            rows={3}
            placeholder='Additional payment notes...'
            className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
          />
        </div>

        {/* Exchange Rate Notes */}
        {paymentCurrency !== baseCurrency && (
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-2'>
              Exchange Rate Notes (Optional)
            </label>
            <textarea
              value={rateNotes}
              onChange={(e) => setRateNotes(e.target.value)}
              rows={2}
              placeholder='Notes about the exchange rate source...'
              className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            />
          </div>
        )}

        {/* Action Buttons */}
        <div className='flex gap-4 pt-4'>
          <button
            type='submit'
            disabled={isLoading}
            className='flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed'
          >
            {isLoading ? 'Processing...' : 'Process Payment'}
          </button>
          {onCancel && (
            <button
              type='button'
              onClick={onCancel}
              disabled={isLoading}
              className='px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed'
            >
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  );
};
