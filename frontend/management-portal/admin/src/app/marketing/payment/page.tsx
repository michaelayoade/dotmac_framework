'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

interface PaymentData {
  token: string
  amount: number
  planType: string
  companyName: string
}

export default function PaymentPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [paymentData, setPaymentData] = useState<PaymentData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isProcessing, setIsProcessing] = useState(false)

  const token = searchParams.get('token')

  useEffect(() => {
    if (token) {
      // Fetch onboarding details using existing API
      fetchOnboardingDetails(token)
    } else {
      router.push('/marketing/signup')
    }
  }, [token, router])

  const fetchOnboardingDetails = async (token: string) => {
    try {
      const response = await fetch(`/api/v1/onboarding/requests/${token}`)
      if (response.ok) {
        const data = await response.json()
        
        // Calculate plan pricing
        const planPricing = {
          starter: 49,
          professional: 149,
          enterprise: 499
        }
        
        setPaymentData({
          token,
          amount: planPricing[data.plan_type as keyof typeof planPricing] || 49,
          planType: data.plan_type,
          companyName: data.tenant_name
        })
      }
    } catch (error) {
      console.error('Failed to fetch onboarding details:', error)
      router.push('/marketing/signup')
    } finally {
      setIsLoading(false)
    }
  }

  const handlePayment = async () => {
    if (!paymentData) return
    
    setIsProcessing(true)

    try {
      // Call existing backend.py payment processing
      const response = await fetch('/marketing/api/payment/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: paymentData.token,
          amount: paymentData.amount,
          plan_type: paymentData.planType,
        }),
      })

      if (response.ok) {
        const result = await response.json()
        
        if (result.success) {
          // Redirect to success page or provisioning status
          router.push(`/marketing/success?token=${paymentData.token}`)
        } else {
          throw new Error(result.message || 'Payment failed')
        }
      } else {
        throw new Error('Payment processing failed')
      }
    } catch (error) {
      console.error('Payment error:', error)
      alert('Payment failed. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading payment details...</p>
        </div>
      </div>
    )
  }

  if (!paymentData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Payment Error</h1>
          <p className="text-gray-600 mb-4">Unable to load payment details.</p>
          <a
            href="/marketing/signup"
            className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700"
          >
            Start Over
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-md mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Complete Your Purchase
          </h1>
          <p className="text-gray-600">
            {paymentData.companyName} • {paymentData.planType} Plan
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-lg p-8">
          {/* Order Summary */}
          <div className="border-b border-gray-200 pb-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Order Summary</h2>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">
                DotMac Platform - {paymentData.planType.charAt(0).toUpperCase() + paymentData.planType.slice(1)} Plan
              </span>
              <span className="font-semibold">${paymentData.amount}/month</span>
            </div>
          </div>

          {/* Payment Form */}
          <div className="space-y-4">
            <div>
              <label htmlFor="cardNumber" className="block text-sm font-medium text-gray-700 mb-2">
                Card Number
              </label>
              <input
                type="text"
                id="cardNumber"
                placeholder="1234 5678 9012 3456"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="expiry" className="block text-sm font-medium text-gray-700 mb-2">
                  Expiry Date
                </label>
                <input
                  type="text"
                  id="expiry"
                  placeholder="MM/YY"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
              </div>
              <div>
                <label htmlFor="cvv" className="block text-sm font-medium text-gray-700 mb-2">
                  CVV
                </label>
                <input
                  type="text"
                  id="cvv"
                  placeholder="123"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
              </div>
            </div>

            <button
              onClick={handlePayment}
              disabled={isProcessing}
              className="w-full bg-purple-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-purple-700 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? 'Processing...' : `Pay $${paymentData.amount}/month`}
            </button>
          </div>

          {/* Security Notice */}
          <div className="mt-6 text-center text-sm text-gray-600">
            <div className="flex items-center justify-center mb-2">
              <svg className="w-4 h-4 text-green-500 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
              </svg>
              Secure Payment
            </div>
            <p>Your payment information is encrypted and secure.</p>
          </div>
        </div>

        <div className="mt-8 text-center">
          <a
            href="/marketing"
            className="text-purple-600 hover:text-purple-800 font-medium"
          >
            ← Back to Home
          </a>
        </div>
      </div>
    </div>
  )
}