/**
 * Currency Management Panel for Customer Multi-Currency Setup
 *
 * Allows customers to configure supported currencies and set base currency.
 * Uses DRY patterns from the unified currency system.
 */

import React, { useState, useEffect } from 'react';
import {
  formatCurrency,
  getSupportedCurrencies,
  getCurrencyInfo,
  type SupportedCurrency,
} from '@dotmac/utils/formatting';

interface CustomerCurrency {
  id: string;
  currency_code: string;
  is_base_currency: boolean;
  is_active: boolean;
  display_name: string | null;
  notes: string | null;
  created_at: string;
}

interface CurrencyManagementPanelProps {
  customerId: string;
  onCurrencyUpdate?: () => void;
}

export const CurrencyManagementPanel: React.FC<CurrencyManagementPanelProps> = ({
  customerId,
  onCurrencyUpdate,
}) => {
  const [currencies, setCurrencies] = useState<CustomerCurrency[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAddingCurrency, setIsAddingCurrency] = useState<boolean>(false);
  const [newCurrency, setNewCurrency] = useState<string>('');
  const [displayName, setDisplayName] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const supportedCurrencies = getSupportedCurrencies();

  // Load customer currencies
  useEffect(() => {
    loadCurrencies();
  }, [customerId]);

  const loadCurrencies = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/customers/${customerId}/currencies`);
      const data = await response.json();

      if (response.ok) {
        setCurrencies(data.currencies || []);
      } else {
        setErrors({ general: data.message || 'Failed to load currencies' });
      }
    } catch (error) {
      setErrors({ general: 'Network error occurred' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddCurrency = async () => {
    if (!newCurrency) {
      setErrors({ newCurrency: 'Please select a currency' });
      return;
    }

    // Check if currency already exists
    if (currencies.some((c) => c.currency_code === newCurrency)) {
      setErrors({ newCurrency: 'Currency already exists' });
      return;
    }

    setErrors({});

    try {
      const currencyInfo = getCurrencyInfo(newCurrency as SupportedCurrency);

      const response = await fetch(`/api/customers/${customerId}/currencies`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          currency_code: newCurrency,
          display_name: displayName || currencyInfo?.name || null,
          notes: notes || null,
          is_base_currency: currencies.length === 0, // First currency is base
          is_active: true,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        await loadCurrencies();
        setIsAddingCurrency(false);
        setNewCurrency('');
        setDisplayName('');
        setNotes('');
        onCurrencyUpdate?.();
      } else {
        setErrors({ general: data.message || 'Failed to add currency' });
      }
    } catch (error) {
      setErrors({ general: 'Network error occurred' });
    }
  };

  const handleSetBaseCurrency = async (currencyId: string) => {
    try {
      const response = await fetch(
        `/api/customers/${customerId}/currencies/${currencyId}/set-base`,
        {
          method: 'POST',
        }
      );

      if (response.ok) {
        await loadCurrencies();
        onCurrencyUpdate?.();
      } else {
        const data = await response.json();
        setErrors({ general: data.message || 'Failed to set base currency' });
      }
    } catch (error) {
      setErrors({ general: 'Network error occurred' });
    }
  };

  const handleToggleActive = async (currencyId: string, isActive: boolean) => {
    try {
      const response = await fetch(`/api/customers/${customerId}/currencies/${currencyId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          is_active: !isActive,
        }),
      });

      if (response.ok) {
        await loadCurrencies();
        onCurrencyUpdate?.();
      } else {
        const data = await response.json();
        setErrors({ general: data.message || 'Failed to update currency' });
      }
    } catch (error) {
      setErrors({ general: 'Network error occurred' });
    }
  };

  const getAvailableCurrencies = () => {
    const usedCurrencies = currencies.map((c) => c.currency_code);
    return supportedCurrencies.filter((currency) => !usedCurrencies.includes(currency));
  };

  if (isLoading) {
    return (
      <div className='bg-white rounded-lg shadow-md p-6'>
        <div className='animate-pulse'>
          <div className='h-6 bg-gray-200 rounded w-1/3 mb-4'></div>
          <div className='space-y-3'>
            <div className='h-4 bg-gray-200 rounded'></div>
            <div className='h-4 bg-gray-200 rounded'></div>
            <div className='h-4 bg-gray-200 rounded'></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className='bg-white rounded-lg shadow-md p-6'>
      <div className='flex justify-between items-center mb-6'>
        <div>
          <h2 className='text-xl font-bold text-gray-900'>Currency Management</h2>
          <p className='text-gray-600 text-sm'>
            Manage supported currencies for multi-currency payments
          </p>
        </div>
        <button
          onClick={() => setIsAddingCurrency(true)}
          disabled={getAvailableCurrencies().length === 0}
          className='px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed'
        >
          Add Currency
        </button>
      </div>

      {errors.general && (
        <div className='mb-4 p-3 bg-red-50 border border-red-200 rounded-md'>
          <div className='text-red-800 text-sm'>{errors.general}</div>
        </div>
      )}

      {/* Add Currency Form */}
      {isAddingCurrency && (
        <div className='mb-6 p-4 bg-gray-50 border border-gray-200 rounded-md'>
          <h3 className='font-semibold text-gray-900 mb-3'>Add New Currency</h3>
          <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Currency</label>
              <select
                value={newCurrency}
                onChange={(e) => {
                  setNewCurrency(e.target.value);
                  const info = getCurrencyInfo(e.target.value as SupportedCurrency);
                  setDisplayName(info?.name || '');
                }}
                className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.newCurrency ? 'border-red-300' : 'border-gray-300'
                }`}
              >
                <option value=''>Select Currency</option>
                {getAvailableCurrencies().map((currency) => {
                  const info = getCurrencyInfo(currency);
                  return (
                    <option key={currency} value={currency}>
                      {currency} - {info?.name}
                    </option>
                  );
                })}
              </select>
              {errors.newCurrency && (
                <p className='text-red-600 text-xs mt-1'>{errors.newCurrency}</p>
              )}
            </div>

            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                Display Name (Optional)
              </label>
              <input
                type='text'
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder='Custom display name'
                className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
              />
            </div>

            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                Notes (Optional)
              </label>
              <input
                type='text'
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder='Additional notes'
                className='w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
              />
            </div>
          </div>

          <div className='flex gap-2 mt-4'>
            <button
              onClick={handleAddCurrency}
              className='px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500'
            >
              Add Currency
            </button>
            <button
              onClick={() => {
                setIsAddingCurrency(false);
                setNewCurrency('');
                setDisplayName('');
                setNotes('');
                setErrors({});
              }}
              className='px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500'
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Currency List */}
      {currencies.length > 0 ? (
        <div className='space-y-3'>
          {currencies.map((currency) => {
            const currencyInfo = getCurrencyInfo(currency.currency_code as SupportedCurrency);
            return (
              <div
                key={currency.id}
                className={`flex items-center justify-between p-4 border rounded-md ${
                  currency.is_base_currency
                    ? 'border-blue-200 bg-blue-50'
                    : currency.is_active
                      ? 'border-gray-200 bg-white'
                      : 'border-gray-200 bg-gray-50'
                }`}
              >
                <div className='flex-1'>
                  <div className='flex items-center gap-2'>
                    <span className='font-semibold text-lg'>
                      {currencyInfo?.symbol} {currency.currency_code}
                    </span>
                    {currency.is_base_currency && (
                      <span className='px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full'>
                        Base Currency
                      </span>
                    )}
                    {!currency.is_active && (
                      <span className='px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full'>
                        Inactive
                      </span>
                    )}
                  </div>
                  <div className='text-sm text-gray-600'>
                    {currency.display_name || currencyInfo?.name}
                  </div>
                  {currency.notes && (
                    <div className='text-xs text-gray-500 mt-1'>{currency.notes}</div>
                  )}
                </div>

                <div className='flex gap-2'>
                  {!currency.is_base_currency && currency.is_active && (
                    <button
                      onClick={() => handleSetBaseCurrency(currency.id)}
                      className='px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500'
                    >
                      Set as Base
                    </button>
                  )}

                  <button
                    onClick={() => handleToggleActive(currency.id, currency.is_active)}
                    disabled={currency.is_base_currency}
                    className={`px-3 py-1 text-xs rounded focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed ${
                      currency.is_active
                        ? 'bg-red-100 text-red-700 hover:bg-red-200'
                        : 'bg-green-100 text-green-700 hover:bg-green-200'
                    }`}
                  >
                    {currency.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className='text-center py-8'>
          <div className='text-gray-500 mb-4'>No currencies configured</div>
          <p className='text-sm text-gray-400'>Add currencies to enable multi-currency payments</p>
        </div>
      )}

      {/* Usage Information */}
      <div className='mt-6 p-4 bg-gray-50 border border-gray-200 rounded-md'>
        <h3 className='font-semibold text-gray-900 mb-2'>How it Works</h3>
        <ul className='text-sm text-gray-600 space-y-1'>
          <li>
            • <strong>Base Currency:</strong> Your primary accounting currency
          </li>
          <li>
            • <strong>Payment Currencies:</strong> Currencies customers can pay in
          </li>
          <li>
            • <strong>Exchange Rates:</strong> Set manually for each transaction
          </li>
          <li>
            • <strong>Conversion:</strong> Payments converted to base currency for accounting
          </li>
        </ul>
      </div>
    </div>
  );
};
