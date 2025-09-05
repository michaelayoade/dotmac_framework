import { Metadata } from 'next'
import { UnifiedHeader } from '@/components/layout/UnifiedHeader'
import { Footer } from '@/components/layout/Footer'
import { LiveChatWidget } from '@/components/marketing/LiveChatWidget'
import { Check, X } from 'lucide-react'

export const metadata: Metadata = {
  title: 'Pricing - DotMac Platform',
  description: 'Simple, transparent pricing for ISPs of all sizes. Start with our free trial and scale as you grow.',
  openGraph: {
    title: 'Pricing - DotMac Platform',
    description: 'Simple, transparent pricing for ISPs of all sizes',
    images: ['/images/og-pricing.jpg'],
  },
}

export default function PricingPage() {
  const plans = [
    {
      name: 'Starter',
      price: 49,
      description: 'Perfect for small ISPs getting started',
      features: [
        'Up to 100 customers',
        'Basic network monitoring',
        'Customer portal',
        'Email support',
        'Core plugins included',
        'Basic reporting'
      ],
      limitations: [
        'Advanced analytics',
        'Custom integrations',
        'Priority support',
        'Custom branding'
      ],
      cta: 'Start Free Trial',
      popular: false
    },
    {
      name: 'Professional',
      price: 149,
      description: 'Most popular for growing ISPs',
      features: [
        'Up to 1,000 customers',
        'Advanced network automation',
        'Full customer portal',
        'Priority support',
        'All plugins included',
        'Advanced analytics',
        'API access',
        'Custom integrations'
      ],
      limitations: [
        'White-label options',
        'Enterprise SLA',
        'Custom plugins'
      ],
      cta: 'Start Free Trial',
      popular: true
    },
    {
      name: 'Enterprise',
      price: 499,
      description: 'For large ISPs and MSPs',
      features: [
        'Unlimited customers',
        'Complete automation suite',
        'White-label solutions',
        'Dedicated support',
        'Custom plugin development',
        'Enterprise SLA',
        'Multi-tenant management',
        'Advanced security features',
        'Custom onboarding'
      ],
      limitations: [],
      cta: 'Contact Sales',
      popular: false
    }
  ]

  return (
    <>
      <UnifiedHeader />
      <div className="bg-gray-50 py-16">
        {/* Header */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Simple, Transparent Pricing
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
            Choose the perfect plan for your ISP. Start with a 14-day free trial, 
            no credit card required. Scale as you grow.
          </p>
          
          <div className="inline-flex items-center bg-green-100 text-green-800 px-4 py-2 rounded-full text-sm font-medium mb-12">
            <span className="mr-2">🎉</span>
            14-day free trial • No setup fees • Cancel anytime
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8">
            {plans.map((plan, index) => (
              <div
                key={plan.name}
                className={`bg-white rounded-2xl shadow-lg overflow-hidden relative ${
                  plan.popular ? 'ring-2 ring-purple-600' : ''
                }`}
              >
                {plan.popular && (
                  <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                    <span className="bg-purple-600 text-white px-4 py-1 rounded-full text-sm font-medium">
                      Most Popular
                    </span>
                  </div>
                )}

                <div className="p-8">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">
                    {plan.name}
                  </h3>
                  <p className="text-gray-600 mb-6">{plan.description}</p>
                  
                  <div className="mb-6">
                    <span className="text-4xl font-bold text-gray-900">
                      ${plan.price}
                    </span>
                    <span className="text-gray-600 ml-2">/month</span>
                  </div>

                  <button
                    className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors mb-8 ${
                      plan.popular
                        ? 'bg-purple-600 text-white hover:bg-purple-700'
                        : 'border border-purple-600 text-purple-600 hover:bg-purple-50'
                    }`}
                  >
                    {plan.cta}
                  </button>

                  {/* Features */}
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                      What's included:
                    </h4>
                    <ul className="space-y-3">
                      {plan.features.map((feature, featureIndex) => (
                        <li key={featureIndex} className="flex items-start">
                          <Check className="w-5 h-5 text-green-500 mr-3 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-700 text-sm">{feature}</span>
                        </li>
                      ))}
                    </ul>

                    {plan.limitations.length > 0 && (
                      <>
                        <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mt-6">
                          Not included:
                        </h4>
                        <ul className="space-y-3">
                          {plan.limitations.map((limitation, limitIndex) => (
                            <li key={limitIndex} className="flex items-start">
                              <X className="w-5 h-5 text-gray-400 mr-3 mt-0.5 flex-shrink-0" />
                              <span className="text-gray-500 text-sm">{limitation}</span>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 mt-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-gray-600">
              Have questions? Our sales team is here to help.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Is there a setup fee?
                </h3>
                <p className="text-gray-600 text-sm">
                  No setup fees. Start your free trial immediately and begin managing your ISP operations.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Can I change plans anytime?
                </h3>
                <p className="text-gray-600 text-sm">
                  Yes, upgrade or downgrade your plan at any time. Changes take effect at your next billing cycle.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  What payment methods do you accept?
                </h3>
                <p className="text-gray-600 text-sm">
                  We accept all major credit cards, PayPal, and ACH transfers for annual plans.
                </p>
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Is my data secure?
                </h3>
                <p className="text-gray-600 text-sm">
                  Yes, we use enterprise-grade encryption and are SOC 2 compliant. Your data is never shared.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Do you offer custom solutions?
                </h3>
                <p className="text-gray-600 text-sm">
                  Enterprise customers can request custom features, integrations, and white-label solutions.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  What if I need help migrating?
                </h3>
                <p className="text-gray-600 text-sm">
                  Our team provides free migration assistance for all new customers. We'll help you get set up.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 mt-20 text-center">
          <div className="bg-purple-600 rounded-2xl p-8 text-white">
            <h2 className="text-3xl font-bold mb-4">
              Ready to Transform Your ISP?
            </h2>
            <p className="text-xl text-purple-100 mb-6">
              Join hundreds of ISPs already using DotMac Platform to streamline operations and grow revenue.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/marketing/signup"
                className="bg-white text-purple-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
              >
                Start Free Trial
              </a>
              <button className="border border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-purple-600 transition-colors">
                Schedule Demo
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <Footer />
      <LiveChatWidget 
        department="sales"
        position="bottom-right"
        triggerText="Questions? Chat with Sales"
      />
    </>
  )
}