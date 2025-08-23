'use client';

import { useState } from 'react';
import { Card } from '@dotmac/styled-components/customer';
import {
  CreditCard,
  Plus,
  Edit3,
  Trash2,
  Check,
  Star,
  AlertCircle,
  Lock,
  Smartphone,
  Building,
  DollarSign,
  Calendar,
  Shield,
  X,
} from 'lucide-react';

interface PaymentMethod {
  id: string;
  type: 'credit_card' | 'debit_card' | 'bank_account' | 'digital_wallet';
  brand?: string;
  last4: string;
  expiryMonth?: number;
  expiryYear?: number;
  holderName: string;
  isDefault: boolean;
  nickname?: string;
  billingAddress: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
  };
  addedDate: string;
  status: 'active' | 'expired' | 'failed';
}

interface PaymentMethodsProps {
  methods: PaymentMethod[];
}

// Mock payment methods data
const mockPaymentMethods: PaymentMethod[] = [
  {
    id: 'pm_1',
    type: 'credit_card',
    brand: 'Visa',
    last4: '1234',
    expiryMonth: 12,
    expiryYear: 2026,
    holderName: 'John Doe',
    isDefault: true,
    nickname: 'Primary Card',
    billingAddress: {
      street: '123 Main St',
      city: 'Anytown',
      state: 'CA',
      zipCode: '12345',
    },
    addedDate: '2024-01-15',
    status: 'active',
  },
  {
    id: 'pm_2',
    type: 'bank_account',
    last4: '9876',
    holderName: 'John Doe',
    isDefault: false,
    nickname: 'Checking Account',
    billingAddress: {
      street: '123 Main St',
      city: 'Anytown',
      state: 'CA',
      zipCode: '12345',
    },
    addedDate: '2024-01-10',
    status: 'active',
  },
  {
    id: 'pm_3',
    type: 'credit_card',
    brand: 'Mastercard',
    last4: '5678',
    expiryMonth: 8,
    expiryYear: 2025,
    holderName: 'John Doe',
    isDefault: false,
    nickname: 'Backup Card',
    billingAddress: {
      street: '123 Main St',
      city: 'Anytown',
      state: 'CA',
      zipCode: '12345',
    },
    addedDate: '2023-11-20',
    status: 'active',
  },
];

export function PaymentMethods({ methods = mockPaymentMethods }: PaymentMethodsProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMethod, setEditingMethod] = useState<string | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>(methods);

  const getPaymentIcon = (type: string, brand?: string) => {
    if (type === 'credit_card' || type === 'debit_card') {
      return <CreditCard className='h-5 w-5 text-blue-600' />;
    } else if (type === 'bank_account') {
      return <Building className='h-5 w-5 text-green-600' />;
    } else if (type === 'digital_wallet') {
      return <Smartphone className='h-5 w-5 text-purple-600' />;
    }
    return <CreditCard className='h-5 w-5 text-gray-600' />;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <Check className='h-4 w-4 text-green-600' />;
      case 'expired':
        return <Calendar className='h-4 w-4 text-red-600' />;
      case 'failed':
        return <AlertCircle className='h-4 w-4 text-red-600' />;
      default:
        return null;
    }
  };

  const formatExpiryDate = (month?: number, year?: number) => {
    if (!month || !year) return '';
    return `${month.toString().padStart(2, '0')}/${year.toString().slice(-2)}`;
  };

  const handleSetDefault = (methodId: string) => {
    setPaymentMethods((prev) =>
      prev.map((method) => ({
        ...method,
        isDefault: method.id === methodId,
      }))
    );
  };

  const handleDeleteMethod = (methodId: string) => {
    if (window.confirm('Are you sure you want to remove this payment method?')) {
      setPaymentMethods((prev) => prev.filter((method) => method.id !== methodId));
    }
  };

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <div>
          <h3 className='text-lg font-semibold text-gray-900'>Payment Methods</h3>
          <p className='mt-1 text-sm text-gray-500'>
            Manage your payment methods and billing preferences
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className='flex items-center rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700'
        >
          <Plus className='mr-2 h-4 w-4' />
          Add Payment Method
        </button>
      </div>

      {/* Add Payment Method Form */}
      {showAddForm && (
        <Card className='p-6 border-blue-200 bg-blue-50'>
          <div className='flex items-center justify-between mb-4'>
            <h4 className='text-lg font-medium text-gray-900'>Add New Payment Method</h4>
            <button
              onClick={() => setShowAddForm(false)}
              className='p-1 hover:bg-blue-100 rounded-full transition-colors'
            >
              <X className='h-5 w-5 text-gray-500' />
            </button>
          </div>
          <form className='space-y-4'>
            <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Payment Type</label>
                <select className='w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'>
                  <option value='credit_card'>Credit Card</option>
                  <option value='debit_card'>Debit Card</option>
                  <option value='bank_account'>Bank Account</option>
                  <option value='digital_wallet'>Digital Wallet</option>
                </select>
              </div>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>
                  Nickname (Optional)
                </label>
                <input
                  type='text'
                  placeholder='e.g., Primary Card'
                  className='w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                />
              </div>
            </div>

            <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Card Number</label>
                <div className='relative'>
                  <input
                    type='text'
                    placeholder='1234 5678 9012 3456'
                    className='w-full rounded-lg border border-gray-300 px-3 py-2 pl-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  />
                  <CreditCard className='absolute left-3 top-2.5 h-4 w-4 text-gray-400' />
                </div>
              </div>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>
                  Cardholder Name
                </label>
                <input
                  type='text'
                  placeholder='John Doe'
                  className='w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                />
              </div>
            </div>

            <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Expiry Month</label>
                <select className='w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'>
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => (
                    <option key={month} value={month}>
                      {month.toString().padStart(2, '0')}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Expiry Year</label>
                <select className='w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'>
                  {Array.from({ length: 10 }, (_, i) => new Date().getFullYear() + i).map(
                    (year) => (
                      <option key={year} value={year}>
                        {year}
                      </option>
                    )
                  )}
                </select>
              </div>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>CVV</label>
                <div className='relative'>
                  <input
                    type='text'
                    placeholder='123'
                    className='w-full rounded-lg border border-gray-300 px-3 py-2 pl-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  />
                  <Shield className='absolute left-3 top-2.5 h-4 w-4 text-gray-400' />
                </div>
              </div>
            </div>

            <div className='space-y-3'>
              <h5 className='font-medium text-gray-900'>Billing Address</h5>
              <div className='grid grid-cols-1 gap-4'>
                <input
                  type='text'
                  placeholder='Street Address'
                  className='w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                />
                <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
                  <input
                    type='text'
                    placeholder='City'
                    className='col-span-2 rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  />
                  <select className='rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'>
                    <option value=''>State</option>
                    <option value='CA'>California</option>
                    <option value='NY'>New York</option>
                    <option value='TX'>Texas</option>
                  </select>
                  <input
                    type='text'
                    placeholder='ZIP Code'
                    className='rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  />
                </div>
              </div>
            </div>

            <div className='flex items-center space-x-3'>
              <input
                type='checkbox'
                id='setDefault'
                className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
              />
              <label htmlFor='setDefault' className='text-sm text-gray-700'>
                Set as default payment method
              </label>
            </div>

            <div className='flex items-center space-x-3'>
              <input
                type='checkbox'
                id='saveSecurely'
                className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                defaultChecked
              />
              <label htmlFor='saveSecurely' className='text-sm text-gray-700'>
                Save this payment method securely for future use
              </label>
            </div>

            <div className='flex space-x-3 pt-4'>
              <button
                type='submit'
                className='flex-1 rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700'
              >
                Add Payment Method
              </button>
              <button
                type='button'
                onClick={() => setShowAddForm(false)}
                className='flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50'
              >
                Cancel
              </button>
            </div>
          </form>

          <div className='mt-4 p-3 bg-blue-100 border border-blue-200 rounded-lg'>
            <div className='flex items-start'>
              <Lock className='h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0' />
              <div className='ml-2'>
                <p className='text-sm text-blue-700'>
                  <strong>Secure Payment Processing:</strong> Your payment information is encrypted
                  and stored securely. We never store your full credit card number.
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Existing Payment Methods */}
      <div className='space-y-4'>
        {paymentMethods.map((method) => (
          <Card key={method.id} className='p-6'>
            <div className='flex items-center justify-between'>
              <div className='flex items-center space-x-4'>
                <div className='flex items-center'>
                  {getPaymentIcon(method.type, method.brand)}
                  {method.isDefault && (
                    <Star className='ml-1 h-4 w-4 text-yellow-500 fill-current' />
                  )}
                </div>

                <div>
                  <div className='flex items-center space-x-2'>
                    <h4 className='font-medium text-gray-900'>
                      {method.nickname || `${method.brand || 'Account'} •••• ${method.last4}`}
                    </h4>
                    {method.isDefault && (
                      <span className='inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800'>
                        Default
                      </span>
                    )}
                    {getStatusIcon(method.status)}
                  </div>
                  <div className='mt-1 text-sm text-gray-500'>
                    {method.type === 'bank_account' ? (
                      <span>Bank Account •••• {method.last4}</span>
                    ) : (
                      <span>
                        {method.brand} •••• {method.last4}
                        {method.expiryMonth && method.expiryYear && (
                          <span className='ml-2'>
                            Expires {formatExpiryDate(method.expiryMonth, method.expiryYear)}
                          </span>
                        )}
                      </span>
                    )}
                  </div>
                  <div className='mt-1 text-xs text-gray-400'>
                    {method.holderName} • Added {new Date(method.addedDate).toLocaleDateString()}
                  </div>
                </div>
              </div>

              <div className='flex items-center space-x-2'>
                {!method.isDefault && (
                  <button
                    onClick={() => handleSetDefault(method.id)}
                    className='rounded-lg border border-gray-300 px-3 py-1 text-sm text-gray-700 transition-colors hover:bg-gray-50'
                  >
                    Make Default
                  </button>
                )}
                <button
                  onClick={() => setEditingMethod(method.id)}
                  className='p-2 text-gray-400 hover:text-gray-600 transition-colors'
                >
                  <Edit3 className='h-4 w-4' />
                </button>
                <button
                  onClick={() => handleDeleteMethod(method.id)}
                  className='p-2 text-red-400 hover:text-red-600 transition-colors'
                  disabled={method.isDefault}
                >
                  <Trash2 className='h-4 w-4' />
                </button>
              </div>
            </div>

            {/* Billing Address */}
            <div className='mt-4 pt-4 border-t border-gray-100'>
              <p className='text-sm text-gray-600'>
                <strong>Billing Address:</strong> {method.billingAddress.street},{' '}
                {method.billingAddress.city}, {method.billingAddress.state}{' '}
                {method.billingAddress.zipCode}
              </p>
            </div>

            {method.status === 'expired' && (
              <div className='mt-4 p-3 bg-red-50 border border-red-200 rounded-lg'>
                <div className='flex items-center'>
                  <AlertCircle className='h-4 w-4 text-red-600 mr-2' />
                  <p className='text-sm text-red-700'>
                    This payment method has expired. Please update your card information.
                  </p>
                  <button className='ml-auto text-sm text-red-600 hover:text-red-800 font-medium'>
                    Update Now
                  </button>
                </div>
              </div>
            )}

            {method.status === 'failed' && (
              <div className='mt-4 p-3 bg-red-50 border border-red-200 rounded-lg'>
                <div className='flex items-center'>
                  <AlertCircle className='h-4 w-4 text-red-600 mr-2' />
                  <p className='text-sm text-red-700'>
                    Recent payment failed with this method. Please verify your information.
                  </p>
                  <button className='ml-auto text-sm text-red-600 hover:text-red-800 font-medium'>
                    Retry Payment
                  </button>
                </div>
              </div>
            )}
          </Card>
        ))}
      </div>

      {/* Security Notice */}
      <Card className='p-4 bg-gray-50 border-gray-200'>
        <div className='flex items-start'>
          <Shield className='h-5 w-5 text-green-600 mt-0.5 flex-shrink-0' />
          <div className='ml-3'>
            <h4 className='font-medium text-gray-900'>Payment Security</h4>
            <p className='mt-1 text-sm text-gray-600'>
              Your payment information is protected with industry-standard encryption and security
              measures. We are PCI DSS compliant and never store your full credit card numbers.
            </p>
            <div className='mt-2 flex items-center space-x-4 text-sm text-gray-500'>
              <span className='flex items-center'>
                <Lock className='mr-1 h-3 w-3' />
                256-bit SSL Encryption
              </span>
              <span className='flex items-center'>
                <Shield className='mr-1 h-3 w-3' />
                PCI DSS Compliant
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Auto-Pay Settings */}
      <Card className='p-6'>
        <h4 className='text-lg font-medium text-gray-900 mb-4'>Auto-Pay Settings</h4>
        <div className='space-y-4'>
          <div className='flex items-center justify-between p-4 border rounded-lg'>
            <div>
              <h5 className='font-medium text-gray-900'>Automatic Payments</h5>
              <p className='text-sm text-gray-600'>Pay your bill automatically each month</p>
            </div>
            <button className='relative inline-flex h-6 w-11 items-center rounded-full bg-blue-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'>
              <span className='inline-block h-4 w-4 translate-x-6 transform rounded-full bg-white transition-transform' />
            </button>
          </div>

          <div className='flex items-center justify-between p-4 border rounded-lg'>
            <div>
              <h5 className='font-medium text-gray-900'>Payment Reminders</h5>
              <p className='text-sm text-gray-600'>Email reminders before due date</p>
            </div>
            <button className='relative inline-flex h-6 w-11 items-center rounded-full bg-blue-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'>
              <span className='inline-block h-4 w-4 translate-x-6 transform rounded-full bg-white transition-transform' />
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}
