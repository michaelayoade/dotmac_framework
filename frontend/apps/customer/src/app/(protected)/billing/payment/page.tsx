'use client';

import { useState } from 'react';
import { MultiCurrencyPaymentForm } from '@dotmac/billing-system';
import { useAuth } from '@dotmac/auth';

interface PaymentPageProps {
  searchParams: {
    invoiceId?: string;
    amount?: string;
    currency?: string;
  };
}

export default function PaymentPage({ searchParams }: PaymentPageProps) {
  const { user } = useAuth();
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [paymentStatus, setPaymentStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handlePaymentSubmit = async (paymentData: any) => {
    setIsProcessing(true);
    setPaymentStatus('idle');
    setErrorMessage('');

    try {
      const response = await fetch('/api/customer/payments/multi-currency', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(paymentData),
      });

      const result = await response.json();

      if (response.ok) {
        setPaymentStatus('success');
        
        // Redirect to success page after delay
        setTimeout(() => {
          window.location.href = `/billing/payment/success?paymentId=${result.payment_id}`;
        }, 2000);
      } else {
        setPaymentStatus('error');
        setErrorMessage(result.message || 'Payment processing failed');
      }
    } catch (error) {
      setPaymentStatus('error');
      setErrorMessage('Network error occurred. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancel = () => {
    window.location.href = '/billing';
  };

  // Success state
  if (paymentStatus === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Payment Successful!</h2>
          <p className="text-gray-600 mb-4">
            Your multi-currency payment has been processed successfully.
          </p>
          <p className="text-sm text-gray-500">
            Redirecting to confirmation page...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Make Payment</h1>
          <p className="text-gray-600 mt-2">
            Pay your invoice using our secure multi-currency payment system
          </p>
        </div>

        {/* Error Message */}
        {paymentStatus === 'error' && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Payment Failed</h3>
                <div className="mt-2 text-sm text-red-700">
                  {errorMessage}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Payment Form */}
        <MultiCurrencyPaymentForm
          customerId={user?.id || ''}
          invoiceId={searchParams.invoiceId}
          invoiceAmount={searchParams.amount ? parseFloat(searchParams.amount) : undefined}
          invoiceCurrency={searchParams.currency}
          onPaymentSubmit={handlePaymentSubmit}
          onCancel={handleCancel}
        />

        {/* Security Notice */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">Secure Payment</h3>
              <div className="mt-2 text-sm text-blue-700">
                Your payment information is encrypted and processed securely. We support multiple currencies with real-time exchange rate conversion.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}