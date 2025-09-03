'use client';

import React, { useState, useCallback } from 'react';
import {
  CreditCard,
  Plus,
  Trash2,
  Edit2,
  Star,
  Shield,
  AlertCircle,
  CheckCircle,
  Eye,
  EyeOff,
  Lock,
} from 'lucide-react';
import { cn, formatPaymentMethod, validateCreditCard, getErrorMessage } from '../utils';
import type { PaymentMethod } from '../types';

interface UniversalPaymentMethodManagerProps {
  paymentMethods: PaymentMethod[];
  onAdd: (methodData: Partial<PaymentMethod>) => Promise<PaymentMethod>;
  onUpdate: (methodId: string, updates: Partial<PaymentMethod>) => Promise<PaymentMethod>;
  onRemove: (methodId: string) => Promise<void>;
  onSetDefault: (methodId: string) => Promise<void>;
  customerId?: string;
  portalType?: 'admin' | 'customer' | 'reseller' | 'management';
  allowMultiple?: boolean;
  className?: string;
}

interface PaymentMethodFormData {
  type: 'credit_card' | 'bank_account' | 'paypal';
  cardNumber: string;
  expiryDate: string;
  cvv: string;
  holderName: string;
  brand?: string;
  routingNumber?: string;
  accountNumber?: string;
  accountType?: 'checking' | 'savings';
  paypalEmail?: string;
}

export function UniversalPaymentMethodManager({
  paymentMethods,
  onAdd,
  onUpdate,
  onRemove,
  onSetDefault,
  customerId,
  portalType = 'customer',
  allowMultiple = true,
  className,
}: UniversalPaymentMethodManagerProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMethod, setEditingMethod] = useState<PaymentMethod | null>(null);
  const [formData, setFormData] = useState<PaymentMethodFormData>({
    type: 'credit_card',
    cardNumber: '',
    expiryDate: '',
    cvv: '',
    holderName: '',
    routingNumber: '',
    accountNumber: '',
    accountType: 'checking',
    paypalEmail: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isProcessing, setIsProcessing] = useState(false);
  const [showSensitive, setShowSensitive] = useState<Record<string, boolean>>({});

  const resetForm = useCallback(() => {
    setFormData({
      type: 'credit_card',
      cardNumber: '',
      expiryDate: '',
      cvv: '',
      holderName: '',
      routingNumber: '',
      accountNumber: '',
      accountType: 'checking',
      paypalEmail: '',
    });
    setErrors({});
    setEditingMethod(null);
    setShowAddForm(false);
  }, []);

  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};

    if (formData.type === 'credit_card') {
      if (!formData.cardNumber || !validateCreditCard(formData.cardNumber)) {
        newErrors.cardNumber = 'Invalid card number';
      }

      if (!formData.expiryDate || !/^\d{2}\/\d{2}$/.test(formData.expiryDate)) {
        newErrors.expiryDate = 'Invalid expiry date (MM/YY)';
      } else {
        const [month, year] = formData.expiryDate.split('/').map(Number);
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear() % 100;
        const currentMonth = currentDate.getMonth() + 1;

        if (year < currentYear || (year === currentYear && month < currentMonth)) {
          newErrors.expiryDate = 'Card has expired';
        }
      }

      if (!formData.cvv || !/^\d{3,4}$/.test(formData.cvv)) {
        newErrors.cvv = 'Invalid CVV';
      }

      if (!formData.holderName.trim()) {
        newErrors.holderName = 'Cardholder name is required';
      }
    }

    if (formData.type === 'bank_account') {
      if (!formData.routingNumber || !/^\d{9}$/.test(formData.routingNumber)) {
        newErrors.routingNumber = 'Invalid routing number (9 digits)';
      }

      if (!formData.accountNumber || formData.accountNumber.length < 4) {
        newErrors.accountNumber = 'Invalid account number';
      }

      if (!formData.holderName.trim()) {
        newErrors.holderName = 'Account holder name is required';
      }
    }

    if (formData.type === 'paypal') {
      if (!formData.paypalEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.paypalEmail)) {
        newErrors.paypalEmail = 'Valid PayPal email is required';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  const getCardBrand = (cardNumber: string): string => {
    const number = cardNumber.replace(/\s/g, '');
    if (/^4/.test(number)) return 'Visa';
    if (/^5[1-5]/.test(number)) return 'Mastercard';
    if (/^3[47]/.test(number)) return 'American Express';
    if (/^6/.test(number)) return 'Discover';
    return 'Unknown';
  };

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!validateForm()) return;

      setIsProcessing(true);
      try {
        const methodData: Partial<PaymentMethod> = {
          type: formData.type,
          last4: '',
          lastFour: '',
          isDefault: paymentMethods.length === 0,
          status: 'active' as const,
        };

        if (formData.type === 'credit_card') {
          methodData.brand = getCardBrand(formData.cardNumber);
          methodData.last4 = formData.cardNumber.slice(-4);
          methodData.lastFour = formData.cardNumber.slice(-4);
          methodData.expiryMonth = parseInt(formData.expiryDate?.split('/')[0] || '0') || undefined;
          methodData.expiryYear =
            parseInt('20' + (formData.expiryDate?.split('/')[1] || '00')) || undefined;
        } else if (formData.type === 'bank_account') {
          methodData.last4 = formData.accountNumber?.slice(-4) || '';
          methodData.lastFour = formData.accountNumber?.slice(-4) || '';
        } else if (formData.type === 'paypal') {
          methodData.last4 = formData.paypalEmail?.split('@')[0]?.slice(-4) || '';
          methodData.lastFour = formData.paypalEmail?.split('@')[0]?.slice(-4) || '';
        }

        if (editingMethod) {
          await onUpdate(editingMethod.id, methodData);
        } else {
          await onAdd(methodData);
        }

        resetForm();
      } catch (error) {
        setErrors({ submit: getErrorMessage(error) });
      } finally {
        setIsProcessing(false);
      }
    },
    [formData, validateForm, paymentMethods.length, editingMethod, onAdd, onUpdate, resetForm]
  );

  const handleRemove = useCallback(
    async (methodId: string) => {
      if (!confirm('Are you sure you want to remove this payment method?')) return;

      setIsProcessing(true);
      try {
        await onRemove(methodId);
      } catch (error) {
        setErrors({ remove: getErrorMessage(error) });
      } finally {
        setIsProcessing(false);
      }
    },
    [onRemove]
  );

  const handleSetDefault = useCallback(
    async (methodId: string) => {
      setIsProcessing(true);
      try {
        await onSetDefault(methodId);
      } catch (error) {
        setErrors({ default: getErrorMessage(error) });
      } finally {
        setIsProcessing(false);
      }
    },
    [onSetDefault]
  );

  const formatCardNumber = (value: string) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const matches = v.match(/\d{4,16}/g);
    const match = (matches && matches[0]) || '';
    const parts = [];
    for (let i = 0, len = match.length; i < len; i += 4) {
      parts.push(match.substring(i, i + 4));
    }
    if (parts.length) {
      return parts.join(' ');
    } else {
      return v;
    }
  };

  const formatExpiryDate = (value: string) => {
    const v = value.replace(/\D/g, '');
    if (v.length >= 2) {
      return `${v.slice(0, 2)}/${v.slice(2, 4)}`;
    }
    return v;
  };

  const getPaymentMethodIcon = (method: PaymentMethod) => {
    switch (method.type) {
      case 'credit_card':
        return <CreditCard className='w-5 h-5 text-blue-600' />;
      case 'bank_account':
        return (
          <div className='w-5 h-5 bg-green-600 rounded flex items-center justify-center text-white text-xs font-bold'>
            B
          </div>
        );
      case 'paypal':
        return (
          <div className='w-5 h-5 bg-blue-500 rounded flex items-center justify-center text-white text-xs font-bold'>
            P
          </div>
        );
      default:
        return <CreditCard className='w-5 h-5 text-gray-400' />;
    }
  };

  const renderPaymentMethodForm = () => (
    <div className='border border-gray-200 rounded-lg p-6 bg-gray-50'>
      <div className='flex items-center justify-between mb-4'>
        <h3 className='text-lg font-medium text-gray-900'>
          {editingMethod ? 'Edit Payment Method' : 'Add Payment Method'}
        </h3>
        <button type='button' onClick={resetForm} className='text-gray-400 hover:text-gray-600'>
          ×
        </button>
      </div>

      <form onSubmit={handleSubmit} className='space-y-4'>
        <div>
          <label className='block text-sm font-medium text-gray-700 mb-2'>
            Payment Method Type
          </label>
          <div className='grid grid-cols-1 md:grid-cols-3 gap-3'>
            {['credit_card', 'bank_account', 'paypal'].map((type) => (
              <button
                key={type}
                type='button'
                onClick={() => setFormData({ ...formData, type: type as any })}
                className={cn(
                  'p-3 border rounded-lg text-left transition-colors',
                  formData.type === type
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <div className='font-medium capitalize'>{type.replace('_', ' ')}</div>
                <div className='text-sm text-gray-500'>
                  {type === 'credit_card' && 'Visa, Mastercard, etc.'}
                  {type === 'bank_account' && 'Direct bank transfer'}
                  {type === 'paypal' && 'PayPal account'}
                </div>
              </button>
            ))}
          </div>
        </div>

        {formData.type === 'credit_card' && (
          <>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Card Number *</label>
              <input
                type='text'
                value={formatCardNumber(formData.cardNumber)}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    cardNumber: e.target.value.replace(/\s/g, ''),
                    brand: getCardBrand(e.target.value.replace(/\s/g, '')),
                  })
                }
                placeholder='1234 5678 9012 3456'
                maxLength={19}
                className={cn(
                  'w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                  errors.cardNumber ? 'border-red-300' : 'border-gray-300'
                )}
              />
              {errors.cardNumber && (
                <div className='flex items-center text-red-600 text-sm mt-1'>
                  <AlertCircle className='w-4 h-4 mr-1' />
                  {errors.cardNumber}
                </div>
              )}
            </div>

            <div className='grid grid-cols-2 gap-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>
                  Expiry Date *
                </label>
                <input
                  type='text'
                  value={formData.expiryDate}
                  onChange={(e) =>
                    setFormData({ ...formData, expiryDate: formatExpiryDate(e.target.value) })
                  }
                  placeholder='MM/YY'
                  maxLength={5}
                  className={cn(
                    'w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                    errors.expiryDate ? 'border-red-300' : 'border-gray-300'
                  )}
                />
                {errors.expiryDate && (
                  <div className='flex items-center text-red-600 text-sm mt-1'>
                    <AlertCircle className='w-4 h-4 mr-1' />
                    {errors.expiryDate}
                  </div>
                )}
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>CVV *</label>
                <div className='relative'>
                  <input
                    type={showSensitive.cvv ? 'text' : 'password'}
                    value={formData.cvv}
                    onChange={(e) =>
                      setFormData({ ...formData, cvv: e.target.value.replace(/\D/g, '') })
                    }
                    placeholder='123'
                    maxLength={4}
                    className={cn(
                      'w-full px-3 py-2 pr-10 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                      errors.cvv ? 'border-red-300' : 'border-gray-300'
                    )}
                  />
                  <button
                    type='button'
                    onClick={() => setShowSensitive({ ...showSensitive, cvv: !showSensitive.cvv })}
                    className='absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600'
                  >
                    {showSensitive.cvv ? (
                      <EyeOff className='w-4 h-4' />
                    ) : (
                      <Eye className='w-4 h-4' />
                    )}
                  </button>
                </div>
                {errors.cvv && (
                  <div className='flex items-center text-red-600 text-sm mt-1'>
                    <AlertCircle className='w-4 h-4 mr-1' />
                    {errors.cvv}
                  </div>
                )}
              </div>
            </div>

            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                Cardholder Name *
              </label>
              <input
                type='text'
                value={formData.holderName}
                onChange={(e) => setFormData({ ...formData, holderName: e.target.value })}
                placeholder='John Doe'
                className={cn(
                  'w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                  errors.holderName ? 'border-red-300' : 'border-gray-300'
                )}
              />
              {errors.holderName && (
                <div className='flex items-center text-red-600 text-sm mt-1'>
                  <AlertCircle className='w-4 h-4 mr-1' />
                  {errors.holderName}
                </div>
              )}
            </div>
          </>
        )}

        {formData.type === 'bank_account' && (
          <>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Account Type *</label>
              <select
                value={formData.accountType}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    accountType: e.target.value as 'checking' | 'savings',
                  })
                }
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
              >
                <option value='checking'>Checking</option>
                <option value='savings'>Savings</option>
              </select>
            </div>

            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                Routing Number *
              </label>
              <input
                type='text'
                value={formData.routingNumber}
                onChange={(e) =>
                  setFormData({ ...formData, routingNumber: e.target.value.replace(/\D/g, '') })
                }
                placeholder='123456789'
                maxLength={9}
                className={cn(
                  'w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                  errors.routingNumber ? 'border-red-300' : 'border-gray-300'
                )}
              />
              {errors.routingNumber && (
                <div className='flex items-center text-red-600 text-sm mt-1'>
                  <AlertCircle className='w-4 h-4 mr-1' />
                  {errors.routingNumber}
                </div>
              )}
            </div>

            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                Account Number *
              </label>
              <div className='relative'>
                <input
                  type={showSensitive.account ? 'text' : 'password'}
                  value={formData.accountNumber}
                  onChange={(e) =>
                    setFormData({ ...formData, accountNumber: e.target.value.replace(/\D/g, '') })
                  }
                  placeholder='Account number'
                  className={cn(
                    'w-full px-3 py-2 pr-10 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                    errors.accountNumber ? 'border-red-300' : 'border-gray-300'
                  )}
                />
                <button
                  type='button'
                  onClick={() =>
                    setShowSensitive({ ...showSensitive, account: !showSensitive.account })
                  }
                  className='absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600'
                >
                  {showSensitive.account ? (
                    <EyeOff className='w-4 h-4' />
                  ) : (
                    <Eye className='w-4 h-4' />
                  )}
                </button>
              </div>
              {errors.accountNumber && (
                <div className='flex items-center text-red-600 text-sm mt-1'>
                  <AlertCircle className='w-4 h-4 mr-1' />
                  {errors.accountNumber}
                </div>
              )}
            </div>

            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                Account Holder Name *
              </label>
              <input
                type='text'
                value={formData.holderName}
                onChange={(e) => setFormData({ ...formData, holderName: e.target.value })}
                placeholder='John Doe'
                className={cn(
                  'w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                  errors.holderName ? 'border-red-300' : 'border-gray-300'
                )}
              />
              {errors.holderName && (
                <div className='flex items-center text-red-600 text-sm mt-1'>
                  <AlertCircle className='w-4 h-4 mr-1' />
                  {errors.holderName}
                </div>
              )}
            </div>
          </>
        )}

        {formData.type === 'paypal' && (
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>PayPal Email *</label>
            <input
              type='email'
              value={formData.paypalEmail}
              onChange={(e) => setFormData({ ...formData, paypalEmail: e.target.value })}
              placeholder='user@paypal.com'
              className={cn(
                'w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                errors.paypalEmail ? 'border-red-300' : 'border-gray-300'
              )}
            />
            {errors.paypalEmail && (
              <div className='flex items-center text-red-600 text-sm mt-1'>
                <AlertCircle className='w-4 h-4 mr-1' />
                {errors.paypalEmail}
              </div>
            )}
          </div>
        )}

        {errors.submit && (
          <div className='bg-red-50 border border-red-200 rounded-lg p-4'>
            <div className='flex items-center text-red-800'>
              <AlertCircle className='w-4 h-4 mr-2' />
              <span className='text-sm'>{errors.submit}</span>
            </div>
          </div>
        )}

        <div className='bg-blue-50 rounded-lg p-4'>
          <div className='flex items-center text-blue-800'>
            <Lock className='w-4 h-4 mr-2' />
            <span className='text-sm'>Your payment information is encrypted and secure</span>
          </div>
        </div>

        <div className='flex justify-end space-x-3'>
          <button
            type='button'
            onClick={resetForm}
            className='px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50'
            disabled={isProcessing}
          >
            Cancel
          </button>
          <button
            type='submit'
            disabled={isProcessing}
            className={cn(
              'px-4 py-2 bg-blue-600 text-white rounded-md font-medium',
              'hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed',
              'flex items-center'
            )}
          >
            {isProcessing && (
              <div className='animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2' />
            )}
            {editingMethod ? 'Update' : 'Add'} Payment Method
          </button>
        </div>
      </form>
    </div>
  );

  return (
    <div className={cn('space-y-6', className)}>
      <div className='flex items-center justify-between'>
        <h2 className='text-xl font-semibold text-gray-900'>Payment Methods</h2>
        {(allowMultiple || paymentMethods.length === 0) && !showAddForm && (
          <button
            onClick={() => setShowAddForm(true)}
            className='flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700'
            disabled={isProcessing}
          >
            <Plus className='w-4 h-4 mr-2' />
            Add Payment Method
          </button>
        )}
      </div>

      {showAddForm && renderPaymentMethodForm()}

      <div className='space-y-4'>
        {paymentMethods.map((method) => (
          <div
            key={method.id}
            className={cn(
              'border rounded-lg p-4 transition-colors',
              method.isDefault
                ? 'border-blue-200 bg-blue-50'
                : 'border-gray-200 bg-white hover:border-gray-300'
            )}
          >
            <div className='flex items-center justify-between'>
              <div className='flex items-center space-x-4'>
                {getPaymentMethodIcon(method)}
                <div>
                  <div className='flex items-center space-x-2'>
                    <span className='font-medium'>{formatPaymentMethod(method)}</span>
                    {method.isDefault && (
                      <span className='inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800'>
                        <Star className='w-3 h-3 mr-1' />
                        Default
                      </span>
                    )}
                  </div>
                  <div className='text-sm text-gray-500'>
                    {method.type === 'credit_card' && method.expiryMonth && method.expiryYear && (
                      <span>
                        Expires {method.expiryMonth}/{method.expiryYear}
                      </span>
                    )}
                    {method.type === 'bank_account' && <span>Bank Account</span>}
                    {method.type === 'paypal' && <span>PayPal Account</span>}
                    <span
                      className={cn(
                        'ml-2 inline-flex items-center',
                        method.status === 'active' ? 'text-green-600' : 'text-red-600'
                      )}
                    >
                      <Shield className='w-3 h-3 mr-1' />
                      {method.status === 'active' ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              </div>

              <div className='flex items-center space-x-2'>
                {!method.isDefault && (
                  <button
                    onClick={() => handleSetDefault(method.id)}
                    className='px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded border border-blue-200'
                    disabled={isProcessing}
                  >
                    Set Default
                  </button>
                )}

                {portalType === 'admin' && (
                  <button
                    onClick={() => {
                      setEditingMethod(method);
                      setShowAddForm(true);
                    }}
                    className='p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded'
                    title='Edit'
                    disabled={isProcessing}
                  >
                    <Edit2 className='w-4 h-4' />
                  </button>
                )}

                {(paymentMethods.length > 1 || !method.isDefault) && (
                  <button
                    onClick={() => handleRemove(method.id)}
                    className='p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded'
                    title='Remove'
                    disabled={isProcessing}
                  >
                    <Trash2 className='w-4 h-4' />
                  </button>
                )}
              </div>
            </div>

            {method.autoPayEnabled && (
              <div className='mt-3 pt-3 border-t border-gray-200'>
                <div className='flex items-center text-sm text-green-600'>
                  <CheckCircle className='w-4 h-4 mr-2' />
                  Auto-pay enabled for recurring charges
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {paymentMethods.length === 0 && !showAddForm && (
        <div className='text-center py-8'>
          <CreditCard className='w-12 h-12 text-gray-400 mx-auto mb-4' />
          <h3 className='text-lg font-medium text-gray-900 mb-2'>No Payment Methods</h3>
          <p className='text-gray-500 mb-4'>Add a payment method to start making payments.</p>
          <button
            onClick={() => setShowAddForm(true)}
            className='inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700'
          >
            <Plus className='w-4 h-4 mr-2' />
            Add Your First Payment Method
          </button>
        </div>
      )}

      {(errors.remove || errors.default) && (
        <div className='bg-red-50 border border-red-200 rounded-lg p-4'>
          <div className='flex items-center text-red-800'>
            <AlertCircle className='w-4 h-4 mr-2' />
            <span className='text-sm'>{errors.remove || errors.default}</span>
          </div>
        </div>
      )}
    </div>
  );
}
