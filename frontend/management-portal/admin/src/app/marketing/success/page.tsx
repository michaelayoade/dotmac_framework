'use client'

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { UnifiedHeader } from '@/components/layout/UnifiedHeader'
import { Footer } from '@/components/layout/Footer'

interface ProvisioningStatus {
  id: string
  status: 'in_progress' | 'completed' | 'failed' | 'validation_failed' | 'manual_required'
  steps_completed: string[]
  next_steps: string[]
  estimated_completion: string
  access_url?: string
  credentials?: {
    admin_url: string
    username: string
    temporary_password: string
    api_endpoint: string
    api_key: string
  }
  error_message?: string
}

function SuccessContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')
  const paymentId = searchParams.get('payment_id')
  
  const [provisioningStatus, setProvisioningStatus] = useState<ProvisioningStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchProvisioningStatus = async () => {
    if (!token) return

    try {
      const response = await fetch(`/api/provisioning/status?token=${token}`)
      if (response.ok) {
        const data = await response.json()
        setProvisioningStatus(data)
      } else {
        setError('Unable to fetch provisioning status')
      }
    } catch (err) {
      setError('Network error while checking status')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProvisioningStatus()
    
    // Poll for updates every 10 seconds while in progress
    const interval = setInterval(() => {
      if (provisioningStatus?.status === 'in_progress') {
        fetchProvisioningStatus()
      }
    }, 10000)

    return () => clearInterval(interval)
  }, [token, provisioningStatus?.status])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600'
      case 'in_progress': return 'text-blue-600'
      case 'failed': case 'validation_failed': return 'text-red-600'
      case 'manual_required': return 'text-yellow-600'
      default: return 'text-gray-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅'
      case 'in_progress': return '⏳'
      case 'failed': case 'validation_failed': return '❌'
      case 'manual_required': return '⚠️'
      default: return '🔄'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <UnifiedHeader />
        <div className="max-w-4xl mx-auto px-4 py-16">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <h1 className="text-2xl font-bold text-gray-900 mt-4">Loading your provisioning status...</h1>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <UnifiedHeader />
      
      <div className="max-w-4xl mx-auto px-4 py-16">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">🎉 Payment Successful!</h1>
          <p className="text-xl text-gray-600">
            Thank you for choosing DotMac Platform. Your ISP management system is being set up.
          </p>
          {paymentId && (
            <p className="text-sm text-gray-500 mt-2">Payment ID: {paymentId}</p>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Status Update Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {provisioningStatus && (
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold text-gray-900">Provisioning Status</h2>
              <div className={`flex items-center space-x-2 ${getStatusColor(provisioningStatus.status)}`}>
                <span className="text-2xl">{getStatusIcon(provisioningStatus.status)}</span>
                <span className="font-medium capitalize">{provisioningStatus.status.replace('_', ' ')}</span>
              </div>
            </div>

            {/* Progress Steps */}
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-3">Completed Steps</h3>
              <ul className="space-y-2">
                {provisioningStatus.steps_completed.map((step, index) => (
                  <li key={index} className="flex items-center space-x-2">
                    <span className="text-green-600">✓</span>
                    <span className="text-gray-700">{step}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Next Steps */}
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-3">Next Steps</h3>
              <ul className="space-y-2">
                {provisioningStatus.next_steps.map((step, index) => (
                  <li key={index} className="flex items-center space-x-2">
                    <span className="text-blue-600">→</span>
                    <span className="text-gray-700">{step}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Estimated Completion */}
            {provisioningStatus.status === 'in_progress' && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <p className="text-blue-800">
                  <strong>Estimated completion:</strong> {new Date(provisioningStatus.estimated_completion).toLocaleString()}
                </p>
              </div>
            )}

            {/* Access Information */}
            {provisioningStatus.status === 'completed' && provisioningStatus.access_url && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                <h3 className="text-lg font-medium text-green-900 mb-3">🚀 Your Platform is Ready!</h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-green-800">
                      <strong>Access URL:</strong> 
                      <a href={provisioningStatus.access_url} target="_blank" rel="noopener noreferrer" 
                         className="ml-2 text-blue-600 hover:text-blue-800 underline">
                        {provisioningStatus.access_url}
                      </a>
                    </p>
                  </div>
                  
                  {provisioningStatus.credentials && (
                    <div className="bg-white rounded border p-4 mt-4">
                      <h4 className="font-medium text-gray-900 mb-2">Login Credentials</h4>
                      <div className="text-sm text-gray-700 space-y-1">
                        <p><strong>Admin Panel:</strong> {provisioningStatus.credentials.admin_url}</p>
                        <p><strong>Username:</strong> {provisioningStatus.credentials.username}</p>
                        <p><strong>Temporary Password:</strong> <code className="bg-gray-100 px-1 rounded">{provisioningStatus.credentials.temporary_password}</code></p>
                        <p><strong>API Endpoint:</strong> {provisioningStatus.credentials.api_endpoint}</p>
                        <p><strong>API Key:</strong> <code className="bg-gray-100 px-1 rounded text-xs">{provisioningStatus.credentials.api_key}</code></p>
                      </div>
                      <div className="mt-3 text-sm text-orange-600">
                        ⚠️ Please change your password after first login and store your API key securely.
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error Information */}
            {(provisioningStatus.status === 'failed' || provisioningStatus.status === 'validation_failed') && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="text-lg font-medium text-red-900 mb-2">Provisioning Issue</h3>
                <p className="text-red-800 mb-3">
                  {provisioningStatus.error_message || 'There was an issue with your provisioning request.'}
                </p>
                <div className="text-sm text-red-700">
                  <p>Our technical team has been notified and will contact you within 2 hours.</p>
                  <p className="mt-1">For immediate assistance: <a href="mailto:support@dotmac.platform" className="underline">support@dotmac.platform</a></p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Support Section */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-3">Need Help?</h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div>
              <h4 className="font-medium text-gray-900">Documentation</h4>
              <p className="text-gray-600 mt-1">
                <a href="/docs" className="text-blue-600 hover:text-blue-800 underline">
                  Getting Started Guide
                </a>
              </p>
            </div>
            <div>
              <h4 className="font-medium text-gray-900">Support</h4>
              <p className="text-gray-600 mt-1">
                <a href="mailto:support@dotmac.platform" className="text-blue-600 hover:text-blue-800 underline">
                  support@dotmac.platform
                </a>
              </p>
            </div>
            <div>
              <h4 className="font-medium text-gray-900">Status Updates</h4>
              <p className="text-gray-600 mt-1">
                <a href="https://status.dotmac.platform" target="_blank" rel="noopener noreferrer" 
                   className="text-blue-600 hover:text-blue-800 underline">
                  System Status Page
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  )
}

export default function SuccessPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    }>
      <SuccessContent />
    </Suspense>
  )
}