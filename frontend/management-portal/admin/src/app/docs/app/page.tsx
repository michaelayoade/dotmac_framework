import { Metadata } from 'next'
import { UnifiedHeader } from '@/components/layout/UnifiedHeader'
import { Footer } from '@/components/layout/Footer'

export const metadata: Metadata = {
  title: 'ISP Framework - Complete ISP Management Platform',
  description: 'Transform your ISP operations with our comprehensive management platform. Automate network management, streamline customer operations, and scale your business with enterprise-grade tools.',
  openGraph: {
    title: 'ISP Framework - Complete ISP Management Platform',
    description: 'Transform your ISP operations with our comprehensive management platform.',
    images: ['/images/og-home.jpg'],
  },
}

export default function HomePage() {
  return (
    <>
      <UnifiedHeader />
      <main className="min-h-screen bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-6">
              ISP Framework Documentation
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
              Transform your ISP operations with our comprehensive management platform. 
              Automate network management, streamline customer operations, and scale your business.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/docs/getting-started"
                className="bg-purple-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-purple-700 transition-colors"
              >
                Get Started
              </a>
              <a
                href="/docs/api-reference"
                className="border border-purple-600 text-purple-600 px-6 py-3 rounded-lg font-semibold hover:bg-purple-50 transition-colors"
              >
                API Reference
              </a>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}