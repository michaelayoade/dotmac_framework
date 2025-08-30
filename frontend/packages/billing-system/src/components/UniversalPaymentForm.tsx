'use client';

import React, { useState, useCallback } from 'react';
import { CreditCard, Lock, AlertCircle, CheckCircle } from 'lucide-react';
import { cn, validateEmail, validateAmount, validateCreditCard, formatCurrency, getErrorMessage } from '../utils';
import type { PaymentMethod, PaymentRequest } from '../types';

interface UniversalPaymentFormProps {
  amount?: number;
  currency?: string;
  onPayment: (paymentData: PaymentRequest) => Promise<void>;
  onCancel?: () => void;
  isProcessing?: boolean;
  existingPaymentMethods?: PaymentMethod[];
  allowNewPaymentMethod?: boolean;
  showSavePaymentMethod?: boolean;
  invoiceId?: string;
  customerId?: string;
  className?: string;
  portalType?: 'admin' | 'customer' | 'reseller' | 'management';
}

export function UniversalPaymentForm({
  amount = 0,
  currency = 'USD',
  onPayment,
  onCancel,
  isProcessing = false,
  existingPaymentMethods = [],
  allowNewPaymentMethod = true,
  showSavePaymentMethod = true,
  invoiceId,
  customerId,
  className,
  portalType = 'customer'
}: UniversalPaymentFormProps) {
  const [paymentMethod, setPaymentMethod] = useState<'existing' | 'new'>('existing');
  const [selectedPaymentMethodId, setSelectedPaymentMethodId] = useState(
    existingPaymentMethods.find(pm => pm.isDefault)?.id || existingPaymentMethods[0]?.id || ''
  );
  const [formData, setFormData] = useState({
    cardNumber: '',
    expiryDate: '',
    cvv: '',
    holderName: '',
    email: '',
    savePaymentMethod: false,
    gateway: 'stripe'
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [step, setStep] = useState<'method' | 'details' | 'confirm'>('method');

  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};

    if (!validateAmount(amount)) {
      newErrors.amount = 'Invalid payment amount';
    }

    if (paymentMethod === 'new') {
      if (!formData.cardNumber || !validateCreditCard(formData.cardNumber)) {
        newErrors.cardNumber = 'Invalid card number';
      }

      if (!formData.expiryDate || !/^\d{2}\/\d{2}$/.test(formData.expiryDate)) {
        newErrors.expiryDate = 'Invalid expiry date (MM/YY)';
      }

      if (!formData.cvv || !/^\d{3,4}$/.test(formData.cvv)) {
        newErrors.cvv = 'Invalid CVV';
      }

      if (!formData.holderName.trim()) {
        newErrors.holderName = 'Cardholder name is required';
      }

      if (portalType === 'admin' && !formData.email) {
        if (!validateEmail(formData.email)) {
          newErrors.email = 'Valid email is required';
        }
      }
    } else if (!selectedPaymentMethodId) {
      newErrors.paymentMethod = 'Please select a payment method';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [amount, paymentMethod, formData, selectedPaymentMethodId, portalType]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    try {
      const paymentData: PaymentRequest = {
        invoiceId: invoiceId || '',
        amount,
        gateway: formData.gateway,
        metadata: {
          portalType,
          customerId,
          ...(paymentMethod === 'new' && {
            savePaymentMethod: formData.savePaymentMethod,
            holderName: formData.holderName,
            email: formData.email
          })
        }
      };

      if (paymentMethod === 'existing') {
        paymentData.paymentMethodId = selectedPaymentMethodId;
      } else {
        // In production, this would tokenize the card details
        paymentData.metadata = {
          ...paymentData.metadata,
          cardNumber: formData.cardNumber,
          expiryDate: formData.expiryDate,
          cvv: formData.cvv
        };
      }

      await onPayment(paymentData);
    } catch (error) {
      setErrors({ submit: getErrorMessage(error) });
    }
  }, [validateForm, amount, invoiceId, customerId, portalType, paymentMethod, selectedPaymentMethodId, formData, onPayment]);

  const formatCardNumber = (value: string) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const matches = v.match(/\d{4,16}/g);
    const match = matches && matches[0] || '';
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

  const StepIndicator = ({ currentStep }: { currentStep: string }) => (
    <div className="flex items-center justify-center mb-6">
      <div className="flex items-center space-x-4">
        {['method', 'details', 'confirm'].map((s, index) => (
          <React.Fragment key={s}>
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
              currentStep === s
                ? "bg-blue-600 text-white"
                : "bg-gray-200 text-gray-600"
            )}>
              {index + 1}
            </div>
            {index < 2 && (
              <div className={cn(
                "w-8 h-0.5",
                ['method', 'details', 'confirm'].indexOf(currentStep) > index
                  ? "bg-blue-600"
                  : "bg-gray-200"
              )} />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );

  const renderMethodStep = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900">Select Payment Method</h3>

      {existingPaymentMethods.length > 0 && (
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">
            Saved Payment Methods
          </label>
          {existingPaymentMethods.map((pm) => (
            <div
              key={pm.id}
              className={cn(
                "border rounded-lg p-4 cursor-pointer transition-colors",
                selectedPaymentMethodId === pm.id && paymentMethod === 'existing'
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300"
              )}
              onClick={() => {
                setPaymentMethod('existing');
                setSelectedPaymentMethodId(pm.id);
              }}
            >
              <div className="flex items-center">
                <input
                  type="radio"
                  name="paymentMethod"
                  value={pm.id}
                  checked={selectedPaymentMethodId === pm.id && paymentMethod === 'existing'}
                  onChange={() => {
                    setPaymentMethod('existing');
                    setSelectedPaymentMethodId(pm.id);
                  }}
                  className="mr-3 text-blue-600"
                />
                <CreditCard className="w-5 h-5 text-gray-400 mr-3" />
                <div>
                  <div className="font-medium">
                    {pm.brand} •••• {pm.last4 || pm.lastFour}
                  </div>
                  <div className="text-sm text-gray-500">
                    {pm.expiryMonth && pm.expiryYear && `Expires ${pm.expiryMonth}/${pm.expiryYear}`}
                    {pm.isDefault && <span className="ml-2 bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs">Default</span>}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {allowNewPaymentMethod && (
        <div
          className={cn(
            "border rounded-lg p-4 cursor-pointer transition-colors",
            paymentMethod === 'new'
              ? "border-blue-500 bg-blue-50"
              : "border-gray-200 hover:border-gray-300"
          )}
          onClick={() => setPaymentMethod('new')}
        >
          <div className="flex items-center">
            <input
              type="radio"
              name="paymentMethod"
              value="new"
              checked={paymentMethod === 'new'}
              onChange={() => setPaymentMethod('new')}
              className="mr-3 text-blue-600"
            />
            <CreditCard className="w-5 h-5 text-gray-400 mr-3" />
            <div>
              <div className="font-medium">Add New Card</div>
              <div className="text-sm text-gray-500">Enter new payment details</div>
            </div>
          </div>
        </div>
      )}

      {errors.paymentMethod && (
        <div className="flex items-center text-red-600 text-sm">
          <AlertCircle className="w-4 h-4 mr-1" />
          {errors.paymentMethod}
        </div>
      )}
    </div>
  );

  const renderDetailsStep = () => {
    if (paymentMethod === 'existing') {
      const selectedPm = existingPaymentMethods.find(pm => pm.id === selectedPaymentMethodId);
      return (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Confirm Payment Details</h3>

          {selectedPm && (
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center">
                <CreditCard className="w-5 h-5 text-gray-400 mr-3" />
                <div>
                  <div className="font-medium">
                    {selectedPm.brand} •••• {selectedPm.last4 || selectedPm.lastFour}
                  </div>
                  <div className="text-sm text-gray-500">
                    {selectedPm.expiryMonth && selectedPm.expiryYear && `Expires ${selectedPm.expiryMonth}/${selectedPm.expiryYear}`}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center text-blue-800">
              <Lock className="w-4 h-4 mr-2" />
              <span className="text-sm">Your payment is secured with 256-bit SSL encryption</span>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">Enter Card Details</h3>

        <div className="grid grid-cols-1 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Card Number
            </label>
            <input
              type="text"
              value={formatCardNumber(formData.cardNumber)}
              onChange={(e) => setFormData({ ...formData, cardNumber: e.target.value.replace(/\s/g, '') })}
              placeholder="1234 5678 9012 3456"
              maxLength={19}
              className={cn(
                "w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                errors.cardNumber ? "border-red-300" : "border-gray-300"
              )}
            />
            {errors.cardNumber && (
              <div className="flex items-center text-red-600 text-sm mt-1">
                <AlertCircle className="w-4 h-4 mr-1" />
                {errors.cardNumber}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Expiry Date
              </label>
              <input
                type="text"
                value={formData.expiryDate}
                onChange={(e) => setFormData({ ...formData, expiryDate: formatExpiryDate(e.target.value) })}
                placeholder="MM/YY"
                maxLength={5}
                className={cn(
                  "w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                  errors.expiryDate ? "border-red-300" : "border-gray-300"
                )}
              />
              {errors.expiryDate && (
                <div className="flex items-center text-red-600 text-sm mt-1">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  {errors.expiryDate}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CVV
              </label>
              <input
                type="text"
                value={formData.cvv}
                onChange={(e) => setFormData({ ...formData, cvv: e.target.value.replace(/\D/g, '') })}
                placeholder="123"
                maxLength={4}
                className={cn(
                  "w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                  errors.cvv ? "border-red-300" : "border-gray-300"
                )}
              />
              {errors.cvv && (
                <div className="flex items-center text-red-600 text-sm mt-1">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  {errors.cvv}
                </div>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Cardholder Name
            </label>
            <input
              type="text"
              value={formData.holderName}
              onChange={(e) => setFormData({ ...formData, holderName: e.target.value })}
              placeholder="John Doe"
              className={cn(
                "w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                errors.holderName ? "border-red-300" : "border-gray-300"
              )}
            />
            {errors.holderName && (
              <div className="flex items-center text-red-600 text-sm mt-1">
                <AlertCircle className="w-4 h-4 mr-1" />
                {errors.holderName}
              </div>
            )}
          </div>

          {portalType === 'admin' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Customer Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="customer@example.com"
                className={cn(
                  "w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                  errors.email ? "border-red-300" : "border-gray-300"
                )}
              />
              {errors.email && (
                <div className="flex items-center text-red-600 text-sm mt-1">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  {errors.email}
                </div>
              )}
            </div>
          )}

          {showSavePaymentMethod && (
            <div className="flex items-center">
              <input
                type="checkbox"
                id="savePaymentMethod"
                checked={formData.savePaymentMethod}
                onChange={(e) => setFormData({ ...formData, savePaymentMethod: e.target.checked })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="savePaymentMethod" className="ml-2 text-sm text-gray-700">
                Save this card for future payments
              </label>
            </div>
          )}
        </div>

        <div className="bg-blue-50 rounded-lg p-4">
          <div className="flex items-center text-blue-800">
            <Lock className="w-4 h-4 mr-2" />
            <span className="text-sm">Your card details are encrypted and secure</span>
          </div>
        </div>
      </div>
    );
  };

  const renderConfirmStep = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900">Confirm Payment</h3>

      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
        <div className="flex justify-between">
          <span className="text-gray-600">Amount</span>
          <span className="font-medium">{formatCurrency(amount, currency)}</span>
        </div>

        {paymentMethod === 'existing' ? (
          <div className="flex justify-between">
            <span className="text-gray-600">Payment Method</span>
            <span className="font-medium">
              {existingPaymentMethods.find(pm => pm.id === selectedPaymentMethodId)?.brand}
              {' '}•••• {existingPaymentMethods.find(pm => pm.id === selectedPaymentMethodId)?.last4 || existingPaymentMethods.find(pm => pm.id === selectedPaymentMethodId)?.lastFour}
            </span>
          </div>
        ) : (
          <div className="flex justify-between">
            <span className="text-gray-600">Payment Method</span>
            <span className="font-medium">
              •••• {formData.cardNumber.slice(-4)}
            </span>
          </div>
        )}

        <div className="flex justify-between">
          <span className="text-gray-600">Gateway</span>
          <span className="font-medium capitalize">{formData.gateway}</span>
        </div>
      </div>

      <div className="bg-green-50 rounded-lg p-4">
        <div className="flex items-center text-green-800">
          <CheckCircle className="w-4 h-4 mr-2" />
          <span className="text-sm">Ready to process payment</span>
        </div>
      </div>
    </div>
  );

  return (
    <div className={cn("bg-white rounded-lg shadow-lg", className)}>
      <div className="p-6">
        <StepIndicator currentStep={step} />

        <form onSubmit={handleSubmit} className="space-y-6">
          {step === 'method' && renderMethodStep()}
          {step === 'details' && renderDetailsStep()}
          {step === 'confirm' && renderConfirmStep()}

          {errors.submit && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center text-red-800">
                <AlertCircle className="w-4 h-4 mr-2" />
                <span className="text-sm">{errors.submit}</span>
              </div>
            </div>
          )}

          <div className="flex justify-between pt-4">
            {step !== 'method' ? (
              <button
                type="button"
                onClick={() => {
                  if (step === 'details') setStep('method');
                  if (step === 'confirm') setStep('details');
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                disabled={isProcessing}
              >
                Back
              </button>
            ) : (
              <div />
            )}

            <div className="flex space-x-3">
              {onCancel && (
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                  disabled={isProcessing}
                >
                  Cancel
                </button>
              )}

              {step === 'confirm' ? (
                <button
                  type="submit"
                  disabled={isProcessing}
                  className={cn(
                    "px-6 py-2 bg-blue-600 text-white rounded-md font-medium",
                    "hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed",
                    "flex items-center"
                  )}
                >
                  {isProcessing && (
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                  )}
                  {isProcessing ? 'Processing...' : `Pay ${formatCurrency(amount, currency)}`}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    if (validateForm()) {
                      if (step === 'method') setStep('details');
                      if (step === 'details') setStep('confirm');
                    }
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  disabled={isProcessing}
                >
                  Continue
                </button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
