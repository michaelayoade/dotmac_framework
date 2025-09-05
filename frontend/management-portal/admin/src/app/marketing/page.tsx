import { Metadata } from 'next'
import { UnifiedHeader } from '@/components/layout/UnifiedHeader'
import { Footer } from '@/components/layout/Footer'
import { LiveChatWidget } from '@/components/marketing/LiveChatWidget'

export const metadata: Metadata = {
  title: 'DotMac Platform - Strategic ISP Management Platform',
  description: 'Open-source, plugin-based ISP management platform with strategic DNS automation and multi-tenant architecture',
  openGraph: {
    title: 'DotMac Platform - Strategic ISP Management Platform',
    description: 'Strategic ISP management platform with plugin-based DNS automation',
    images: ['/images/og-marketing.jpg'],
  },
}

export default function MarketingPage() {
  return (
    <>
      <UnifiedHeader />
      <div className="bg-gray-50 text-gray-800">
      {/* Hero Section */}
      <section className="gradient-bg hero-pattern min-h-screen flex items-center justify-center text-white">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <div className="flex items-center justify-center mb-8">
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-2xl flex items-center justify-center mr-4">
              <span className="text-3xl font-bold">D</span>
            </div>
            <h1 className="text-5xl font-bold">DotMac Platform</h1>
          </div>
          
          <h2 className="text-2xl md:text-3xl mb-6 font-light">
            Strategic ISP Management Platform
          </h2>
          
          <p className="text-xl md:text-2xl mb-8 opacity-90 max-w-4xl mx-auto leading-relaxed">
            Leverage your existing infrastructure with our plugin-based DNS automation, 
            multi-tenant architecture, and vendor-neutral approach to ISP management.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a
              href="/marketing/signup"
              className="bg-white text-purple-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors text-lg"
            >
              Start Free Trial
            </a>
            <a
              href="/docs"
              className="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-purple-600 transition-colors text-lg"
            >
              View Documentation
            </a>
          </div>
          
          <div className="mt-12">
            <p className="text-sm opacity-75 mb-4">Trusted by ISPs worldwide</p>
            <div className="flex justify-center items-center space-x-8 opacity-60">
              <div className="h-8 w-24 bg-white bg-opacity-20 rounded"></div>
              <div className="h-8 w-24 bg-white bg-opacity-20 rounded"></div>
              <div className="h-8 w-24 bg-white bg-opacity-20 rounded"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Key Benefits */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-6">
              Strategic Infrastructure Usage
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Don't rebuild what you already have. Our platform integrates seamlessly 
              with your existing systems while providing modern management capabilities.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="feature-card bg-gray-50 p-8 rounded-2xl">
              <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-4">Plugin-Based Architecture</h3>
              <p className="text-gray-600">
                Extend functionality without touching core code. Add DNS providers, 
                billing systems, or monitoring tools as needed.
              </p>
            </div>

            <div className="feature-card bg-gray-50 p-8 rounded-2xl">
              <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-4">Multi-Tenant Ready</h3>
              <p className="text-gray-600">
                Built for service providers from day one. Manage multiple clients 
                with complete isolation and customization.
              </p>
            </div>

            <div className="feature-card bg-gray-50 p-8 rounded-2xl">
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-4">Vendor Neutral</h3>
              <p className="text-gray-600">
                Work with any DNS provider, any hosting solution, any monitoring system. 
                No vendor lock-in, maximum flexibility.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 gradient-bg text-white text-center">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Ready to Transform Your ISP Operations?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Join hundreds of ISPs already using DotMac Platform to streamline 
            their operations and scale their business.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a
              href="/marketing/signup"
              className="bg-white text-purple-600 px-8 py-4 rounded-lg font-semibold hover:bg-gray-100 transition-colors text-lg"
            >
              Start Your Free Trial
            </a>
            <a
              href="/marketing/contact"
              className="border-2 border-white text-white px-8 py-4 rounded-lg font-semibold hover:bg-white hover:text-purple-600 transition-colors text-lg"
            >
              Schedule Demo
            </a>
          </div>
        </div>
      </section>
      </div>
      <Footer />
      <LiveChatWidget 
        department="sales"
        position="bottom-right"
        triggerText="Chat with Sales"
      />
    </>
  )
}