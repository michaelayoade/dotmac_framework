'use client';

import { useState, useEffect } from 'react';
import { Card } from '@dotmac/styled-components/customer';
import {
  CreditCard,
  DollarSign,
  Calendar,
  CheckCircle,
  AlertCircle,
  Clock,
  Smartphone,
  Zap,
  ShieldCheck,
  Receipt,
  ArrowRight,
  Lock,
  Star,
} from 'lucide-react';

interface QuickPaymentProps {
  currentBalance?: number;
  nextBillAmount?: number;
  nextBillDate?: string;
  isAutoPayEnabled?: boolean;
}

export function QuickPayment({
  currentBalance = 0,
  nextBillAmount = 109.98,
  nextBillDate = '2024-02-15',
  isAutoPayEnabled = true,
}: QuickPaymentProps) {
  const [selectedAmount, setSelectedAmount] = useState<'current' | 'next' | 'custom'>('current');
  const [customAmount, setCustomAmount] = useState('');
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('pm_1');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [showSecurityInfo, setShowSecurityInfo] = useState(false);

  // Mock payment methods
  const paymentMethods = [
    {
      id: 'pm_1',
      type: 'credit_card',
      brand: 'Visa',
      last4: '1234',
      isDefault: true,
      nickname: 'Primary Card',
    },
    {
      id: 'pm_2',
      type: 'bank_account',
      last4: '9876',
      isDefault: false,
      nickname: 'Checking Account',
    },
  ];

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getPaymentAmount = () => {
    switch (selectedAmount) {
      case 'current':
        return currentBalance;
      case 'next':
        return nextBillAmount;
      case 'custom':
        return parseFloat(customAmount) || 0;
      default:
        return 0;
    }
  };

  const handlePayment = async () => {
    setIsProcessing(true);

    // Simulate payment processing
    await new Promise((resolve) => setTimeout(resolve, 2000));

    setIsProcessing(false);
    setShowConfirmation(true);
  };

  const resetPayment = () => {
    setShowConfirmation(false);
    setSelectedAmount('current');
    setCustomAmount('');
  };

  if (showConfirmation) {
    return (
      <Card className='p-6 border-green-200 bg-green-50'>
        <div className='text-center'>
          <div className='mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100'>
            <CheckCircle className='h-8 w-8 text-green-600' />
          </div>
          <h3 className='text-xl font-semibold text-green-900 mb-2'>Payment Successful!</h3>
          <p className='text-green-700 mb-4'>
            Your payment of {formatCurrency(getPaymentAmount())} has been processed successfully.
          </p>

          <div className='bg-white border border-green-200 rounded-lg p-4 mb-6'>
            <div className='grid grid-cols-2 gap-4 text-sm'>
              <div className='text-left'>
                <span className='text-gray-600'>Transaction ID:</span>
                <p className='font-mono font-medium'>TXN-{Date.now()}</p>
              </div>
              <div className='text-left'>
                <span className='text-gray-600'>Payment Method:</span>
                <p className='font-medium'>
                  {paymentMethods.find((m) => m.id === selectedPaymentMethod)?.nickname}
                </p>
              </div>
              <div className='text-left'>
                <span className='text-gray-600'>Amount:</span>
                <p className='font-medium text-green-600'>{formatCurrency(getPaymentAmount())}</p>
              </div>
              <div className='text-left'>
                <span className='text-gray-600'>Date:</span>
                <p className='font-medium'>{new Date().toLocaleDateString()}</p>
              </div>
            </div>
          </div>

          <div className='flex flex-col sm:flex-row gap-3'>
            <button
              onClick={resetPayment}
              className='flex-1 rounded-lg bg-green-600 px-4 py-2 text-white transition-colors hover:bg-green-700'
            >
              <Receipt className='mr-2 h-4 w-4 inline' />
              Email Receipt
            </button>
            <button
              onClick={resetPayment}
              className='flex-1 rounded-lg border border-green-300 px-4 py-2 text-green-700 transition-colors hover:bg-green-100'
            >
              Make Another Payment
            </button>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className='space-y-6'>
      <Card className='p-6'>
        <div className='mb-6'>
          <div className='flex items-center justify-between mb-2'>
            <h3 className='text-xl font-semibold text-gray-900'>Quick Payment</h3>
            <div className='flex items-center text-sm text-green-600'>
              <ShieldCheck className='mr-1 h-4 w-4' />
              Secure
            </div>
          </div>
          <p className='text-gray-600'>Make a quick payment with just a few taps</p>
        </div>

        {/* Current Balance Alert */}
        {currentBalance > 0 && (
          <div className='mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg'>
            <div className='flex items-start'>
              <AlertCircle className='h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0' />
              <div className='ml-3'>
                <h4 className='font-medium text-yellow-900'>Outstanding Balance</h4>
                <p className='text-sm text-yellow-700 mt-1'>
                  You have a current balance of {formatCurrency(currentBalance)} that needs to be
                  paid.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Auto-Pay Status */}
        {isAutoPayEnabled && currentBalance === 0 && (
          <div className='mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'>
            <div className='flex items-start'>
              <Zap className='h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0' />
              <div className='ml-3'>
                <h4 className='font-medium text-blue-900'>Auto-Pay Enabled</h4>
                <p className='text-sm text-blue-700 mt-1'>
                  Your next bill of {formatCurrency(nextBillAmount)} will be automatically paid on{' '}
                  {formatDate(nextBillDate)}.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Payment Amount Selection */}
        <div className='mb-6'>
          <h4 className='font-medium text-gray-900 mb-3'>Select Payment Amount</h4>
          <div className='space-y-3'>
            {/* Current Balance Option */}
            {currentBalance > 0 && (
              <label className='flex items-center p-4 border-2 rounded-lg cursor-pointer transition-colors hover:bg-gray-50 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50'>
                <input
                  type='radio'
                  name='amount'
                  value='current'
                  checked={selectedAmount === 'current'}
                  onChange={() => setSelectedAmount('current')}
                  className='h-4 w-4 text-blue-600'
                />
                <div className='ml-3 flex-grow'>
                  <div className='flex items-center justify-between'>
                    <div>
                      <p className='font-medium text-gray-900'>Pay Current Balance</p>
                      <p className='text-sm text-gray-600'>Clear your outstanding balance</p>
                    </div>
                    <div className='text-right'>
                      <p className='font-bold text-lg text-red-600'>
                        {formatCurrency(currentBalance)}
                      </p>
                      {currentBalance > 0 && (
                        <span className='inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800'>
                          Overdue
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </label>
            )}

            {/* Next Bill Option */}
            <label className='flex items-center p-4 border-2 rounded-lg cursor-pointer transition-colors hover:bg-gray-50 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50'>
              <input
                type='radio'
                name='amount'
                value='next'
                checked={selectedAmount === 'next'}
                onChange={() => setSelectedAmount('next')}
                className='h-4 w-4 text-blue-600'
              />
              <div className='ml-3 flex-grow'>
                <div className='flex items-center justify-between'>
                  <div>
                    <p className='font-medium text-gray-900'>Pay Next Bill</p>
                    <p className='text-sm text-gray-600'>Due {formatDate(nextBillDate)}</p>
                  </div>
                  <div className='text-right'>
                    <p className='font-bold text-lg text-gray-900'>
                      {formatCurrency(nextBillAmount)}
                    </p>
                    <div className='flex items-center text-xs text-gray-500'>
                      <Calendar className='mr-1 h-3 w-3' />
                      {Math.ceil(
                        (new Date(nextBillDate).getTime() - new Date().getTime()) /
                          (1000 * 3600 * 24)
                      )}{' '}
                      days
                    </div>
                  </div>
                </div>
              </div>
            </label>

            {/* Custom Amount Option */}
            <label className='flex items-center p-4 border-2 rounded-lg cursor-pointer transition-colors hover:bg-gray-50 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50'>
              <input
                type='radio'
                name='amount'
                value='custom'
                checked={selectedAmount === 'custom'}
                onChange={() => setSelectedAmount('custom')}
                className='h-4 w-4 text-blue-600'
              />
              <div className='ml-3 flex-grow'>
                <div className='flex items-center justify-between'>
                  <div className='flex-grow'>
                    <p className='font-medium text-gray-900'>Custom Amount</p>
                    <p className='text-sm text-gray-600'>Enter any amount you'd like to pay</p>
                  </div>
                  <div className='ml-4'>
                    {selectedAmount === 'custom' && (
                      <div className='relative'>
                        <DollarSign className='absolute left-3 top-2.5 h-4 w-4 text-gray-400' />
                        <input
                          type='number'
                          value={customAmount}
                          onChange={(e) => setCustomAmount(e.target.value)}
                          placeholder='0.00'
                          min='0.01'
                          step='0.01'
                          className='w-32 rounded-lg border border-gray-300 px-3 py-2 pl-10 text-right focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Payment Method Selection */}
        <div className='mb-6'>
          <h4 className='font-medium text-gray-900 mb-3'>Payment Method</h4>
          <div className='space-y-2'>
            {paymentMethods.map((method) => (
              <label
                key={method.id}
                className='flex items-center p-3 border rounded-lg cursor-pointer transition-colors hover:bg-gray-50 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50'
              >
                <input
                  type='radio'
                  name='payment_method'
                  value={method.id}
                  checked={selectedPaymentMethod === method.id}
                  onChange={() => setSelectedPaymentMethod(method.id)}
                  className='h-4 w-4 text-blue-600'
                />
                <div className='ml-3 flex items-center justify-between flex-grow'>
                  <div className='flex items-center'>
                    {method.type === 'credit_card' ? (
                      <CreditCard className='h-5 w-5 text-blue-600 mr-2' />
                    ) : (
                      <Smartphone className='h-5 w-5 text-green-600 mr-2' />
                    )}
                    <div>
                      <p className='font-medium text-gray-900'>{method.nickname}</p>
                      <p className='text-sm text-gray-600'>
                        {method.brand} •••• {method.last4}
                      </p>
                    </div>
                  </div>
                  {method.isDefault && <Star className='h-4 w-4 text-yellow-500 fill-current' />}
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Payment Summary */}
        <div className='mb-6 p-4 bg-gray-50 rounded-lg border'>
          <h4 className='font-medium text-gray-900 mb-2'>Payment Summary</h4>
          <div className='space-y-2 text-sm'>
            <div className='flex justify-between'>
              <span className='text-gray-600'>Amount:</span>
              <span className='font-medium'>{formatCurrency(getPaymentAmount())}</span>
            </div>
            <div className='flex justify-between'>
              <span className='text-gray-600'>Processing Fee:</span>
              <span className='font-medium text-green-600'>FREE</span>
            </div>
            <div className='flex justify-between'>
              <span className='text-gray-600'>Payment Method:</span>
              <span className='font-medium'>
                {paymentMethods.find((m) => m.id === selectedPaymentMethod)?.nickname}
              </span>
            </div>
            <div className='border-t pt-2 flex justify-between font-semibold'>
              <span>Total:</span>
              <span className='text-lg'>{formatCurrency(getPaymentAmount())}</span>
            </div>
          </div>
        </div>

        {/* Payment Button */}
        <button
          onClick={handlePayment}
          disabled={isProcessing || getPaymentAmount() <= 0}
          className={`w-full rounded-lg px-6 py-3 font-medium transition-all duration-200 ${
            isProcessing || getPaymentAmount() <= 0
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700 hover:shadow-lg transform hover:-translate-y-0.5'
          }`}
        >
          <div className='flex items-center justify-center'>
            {isProcessing ? (
              <>
                <div className='mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent' />
                Processing Payment...
              </>
            ) : (
              <>
                <Lock className='mr-2 h-4 w-4' />
                Pay {formatCurrency(getPaymentAmount())} Securely
                <ArrowRight className='ml-2 h-4 w-4' />
              </>
            )}
          </div>
        </button>

        {/* Security Notice */}
        <div className='mt-4 text-center'>
          <button
            onClick={() => setShowSecurityInfo(!showSecurityInfo)}
            className='text-sm text-gray-600 hover:text-gray-800 underline'
          >
            How is my payment secured?
          </button>

          {showSecurityInfo && (
            <div className='mt-3 p-3 bg-gray-50 rounded-lg text-left text-sm text-gray-600'>
              <div className='flex items-start'>
                <ShieldCheck className='h-4 w-4 text-green-600 mt-0.5 flex-shrink-0' />
                <div className='ml-2'>
                  <p className='font-medium text-gray-900 mb-1'>Your payment is protected by:</p>
                  <ul className='space-y-1 text-xs'>
                    <li>• 256-bit SSL encryption</li>
                    <li>• PCI DSS compliance</li>
                    <li>• Fraud monitoring and detection</li>
                    <li>• Secure tokenization (we never store card numbers)</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Quick Payment Tips */}
      <Card className='p-4 bg-blue-50 border-blue-200'>
        <h4 className='font-medium text-blue-900 mb-2'>💡 Payment Tips</h4>
        <ul className='space-y-1 text-sm text-blue-700'>
          <li>• Payments are processed instantly and will reflect in your account immediately</li>
          <li>• Set up Auto-Pay to never miss a payment and avoid late fees</li>
          <li>• You can make partial payments anytime to reduce your balance</li>
          <li>• All payments include email confirmations and receipts</li>
        </ul>
      </Card>
    </div>
  );
}
