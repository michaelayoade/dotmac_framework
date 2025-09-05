'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  CheckCircle, 
  ArrowRight, 
  Shield,
  Clock,
  Users,
  Zap,
  AlertCircle,
  Loader2,
  Crown,
  Star
} from 'lucide-react'

interface SignupForm {
  companyName: string
  firstName: string
  lastName: string
  email: string
  phone: string
  customerCount: string
  plan: string
  agreedToTerms: boolean
  wantsUpdates: boolean
}

interface PlanDetails {
  name: string
  price: string
  period: string
  trialDays: number
  features: string[]
  popular: boolean
}

const planDetails: Record<string, PlanDetails> = {
  starter: {
    name: 'Starter',
    price: 'Free',
    period: 'forever',
    trialDays: 0,
    features: ['Up to 100 customers', 'Basic monitoring', 'Email support'],
    popular: false
  },
  professional: {
    name: 'Professional',
    price: '$299',
    period: 'per month',
    trialDays: 14,
    features: ['Up to 5,000 customers', 'Advanced automation', 'Priority support'],
    popular: true
  },
  enterprise: {
    name: 'Enterprise',
    price: 'Custom',
    period: 'pricing',
    trialDays: 30,
    features: ['Unlimited customers', 'White-label', 'Dedicated support'],
    popular: false
  }
}

export default function SignupPage() {
  const searchParams = useSearchParams()
  const [selectedPlan, setSelectedPlan] = useState(searchParams?.get('plan') || 'professional')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [formData, setFormData] = useState<SignupForm>({
    companyName: '',
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    customerCount: '',
    plan: selectedPlan,
    agreedToTerms: false,
    wantsUpdates: false
  })

  useEffect(() => {
    setFormData(prev => ({ ...prev, plan: selectedPlan }))
  }, [selectedPlan])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }))
  }

  const validateForm = (): boolean => {
    if (!formData.companyName || !formData.firstName || !formData.lastName || !formData.email) {
      setError('Please fill in all required fields')
      return false
    }
    
    if (!formData.email.includes('@') || !formData.email.includes('.')) {
      setError('Please enter a valid email address')
      return false
    }
    
    if (!formData.agreedToTerms) {
      setError('Please agree to the Terms of Service')
      return false
    }
    
    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (!validateForm()) return
    
    setIsLoading(true)
    
    try {
      // This would integrate with the DotMac management platform API
      const response = await fetch('/api/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          source: 'marketing_website',
          planDetails: planDetails[selectedPlan]
        })
      })

      if (!response.ok) {
        throw new Error('Signup failed. Please try again.')
      }

      const result = await response.json()
      
      // Success - redirect to management platform or show success
      setSuccess(true)
      
      // In production, this would redirect to the management platform
      // with the provisioned account details
      setTimeout(() => {
        window.location.href = `${process.env.NEXT_PUBLIC_MANAGEMENT_PLATFORM_URL}/onboarding?token=${result.token}&plan=${selectedPlan}`
      }, 2000)
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Something went wrong. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const currentPlan = planDetails[selectedPlan]

  if (success) {
    return (
      <>
        <Header />
        <main className="pt-32 pb-16">
          <div className="container-custom">
            <div className="max-w-2xl mx-auto text-center">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mb-6 mx-auto">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              
              <h1 className="text-3xl font-bold text-foreground mb-4">
                Welcome to ISP Framework!
              </h1>
              
              <p className="text-lg text-muted-foreground mb-8">
                Your account is being set up. You'll be redirected to your management dashboard in a moment.
              </p>
              
              <div className="bg-muted/50 rounded-xl p-6 mb-8">
                <h3 className="font-semibold text-foreground mb-4">What happens next:</h3>
                <div className="space-y-3 text-left">
                  <div className="flex items-center">
                    <CheckCircle className="w-5 h-5 text-green-600 mr-3" />
                    <span className="text-sm">Account provisioned automatically</span>
                  </div>
                  <div className="flex items-center">
                    <CheckCircle className="w-5 h-5 text-green-600 mr-3" />
                    <span className="text-sm">Test environment configured</span>
                  </div>
                  <div className="flex items-center">
                    <Clock className="w-5 h-5 text-blue-600 mr-3" />
                    <span className="text-sm">
                      {currentPlan.trialDays > 0 ? `${currentPlan.trialDays}-day trial` : 'Free access'} activated
                    </span>
                  </div>
                  <div className="flex items-center">
                    <Clock className="w-5 h-5 text-blue-600 mr-3" />
                    <span className="text-sm">Welcome email sent with login details</span>
                  </div>
                </div>
              </div>
              
              <div className="text-sm text-muted-foreground">
                Redirecting you to your dashboard...
                <Loader2 className="w-4 h-4 animate-spin inline ml-2" />
              </div>
            </div>
          </div>
        </main>
        <Footer />
      </>
    )
  }

  return (
    <>
      <Header />
      <main className="pt-32 pb-16">
        <div className="container-custom">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="text-center mb-12">
              <Badge variant="secondary" className="mb-4">
                {currentPlan.trialDays > 0 ? `${currentPlan.trialDays}-Day Free Trial` : 'Free Forever'}
              </Badge>
              <h1 className="text-3xl font-bold text-foreground mb-4">
                Start your ISP transformation today
              </h1>
              <p className="text-lg text-muted-foreground">
                Get your ISP management platform set up in minutes, not months.
              </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-12">
              {/* Form */}
              <div>
                <Card>
                  <CardHeader>
                    <CardTitle>Create Your Account</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-6">
                      {error && (
                        <div className="flex items-center p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                          <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
                          <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
                        </div>
                      )}

                      {/* Plan Selection */}
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-3">
                          Select Plan
                        </label>
                        <div className="grid grid-cols-3 gap-3">
                          {Object.entries(planDetails).map(([key, plan]) => (
                            <button
                              key={key}
                              type="button"
                              onClick={() => setSelectedPlan(key)}
                              className={`relative p-3 rounded-lg border text-center transition-colors ${
                                selectedPlan === key
                                  ? 'border-primary bg-primary/5'
                                  : 'border-border hover:border-primary/50'
                              }`}
                            >
                              {plan.popular && (
                                <Star className="absolute -top-2 -right-2 w-4 h-4 text-yellow-500 fill-current" />
                              )}
                              <div className="font-medium text-sm">{plan.name}</div>
                              <div className="text-xs text-muted-foreground">{plan.price}</div>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Company Information */}
                      <div>
                        <label htmlFor="companyName" className="block text-sm font-medium text-foreground mb-2">
                          Company Name *
                        </label>
                        <input
                          type="text"
                          id="companyName"
                          name="companyName"
                          required
                          value={formData.companyName}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                          placeholder="Your ISP Company Name"
                        />
                      </div>

                      {/* Personal Information */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label htmlFor="firstName" className="block text-sm font-medium text-foreground mb-2">
                            First Name *
                          </label>
                          <input
                            type="text"
                            id="firstName"
                            name="firstName"
                            required
                            value={formData.firstName}
                            onChange={handleInputChange}
                            className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                            placeholder="John"
                          />
                        </div>
                        <div>
                          <label htmlFor="lastName" className="block text-sm font-medium text-foreground mb-2">
                            Last Name *
                          </label>
                          <input
                            type="text"
                            id="lastName"
                            name="lastName"
                            required
                            value={formData.lastName}
                            onChange={handleInputChange}
                            className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                            placeholder="Doe"
                          />
                        </div>
                      </div>

                      {/* Contact Information */}
                      <div>
                        <label htmlFor="email" className="block text-sm font-medium text-foreground mb-2">
                          Business Email *
                        </label>
                        <input
                          type="email"
                          id="email"
                          name="email"
                          required
                          value={formData.email}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                          placeholder="john@yourcompany.com"
                        />
                      </div>

                      <div>
                        <label htmlFor="phone" className="block text-sm font-medium text-foreground mb-2">
                          Phone Number
                        </label>
                        <input
                          type="tel"
                          id="phone"
                          name="phone"
                          value={formData.phone}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                          placeholder="+1 (555) 123-4567"
                        />
                      </div>

                      {/* Business Information */}
                      <div>
                        <label htmlFor="customerCount" className="block text-sm font-medium text-foreground mb-2">
                          Current Customer Count
                        </label>
                        <select
                          id="customerCount"
                          name="customerCount"
                          value={formData.customerCount}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                        >
                          <option value="">Select range</option>
                          <option value="0-100">0-100 customers</option>
                          <option value="101-500">101-500 customers</option>
                          <option value="501-1000">501-1,000 customers</option>
                          <option value="1001-5000">1,001-5,000 customers</option>
                          <option value="5001+">5,001+ customers</option>
                        </select>
                      </div>

                      {/* Terms and Updates */}
                      <div className="space-y-3">
                        <div className="flex items-start">
                          <input
                            type="checkbox"
                            id="agreedToTerms"
                            name="agreedToTerms"
                            checked={formData.agreedToTerms}
                            onChange={handleInputChange}
                            className="mt-1 mr-3"
                            required
                          />
                          <label htmlFor="agreedToTerms" className="text-sm text-foreground">
                            I agree to the{' '}
                            <a href="/terms" className="text-primary hover:underline" target="_blank">
                              Terms of Service
                            </a>{' '}
                            and{' '}
                            <a href="/privacy" className="text-primary hover:underline" target="_blank">
                              Privacy Policy
                            </a>
                          </label>
                        </div>
                        
                        <div className="flex items-start">
                          <input
                            type="checkbox"
                            id="wantsUpdates"
                            name="wantsUpdates"
                            checked={formData.wantsUpdates}
                            onChange={handleInputChange}
                            className="mt-1 mr-3"
                          />
                          <label htmlFor="wantsUpdates" className="text-sm text-foreground">
                            I want to receive product updates and ISP industry insights
                          </label>
                        </div>
                      </div>

                      <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
                        {isLoading ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Setting up your account...
                          </>
                        ) : (
                          <>
                            {currentPlan.trialDays > 0 ? `Start ${currentPlan.trialDays}-Day Trial` : 'Create Free Account'}
                            <ArrowRight className="w-4 h-4 ml-2" />
                          </>
                        )}
                      </Button>
                    </form>
                  </CardContent>
                </Card>
              </div>

              {/* Plan Summary */}
              <div>
                <Card className="sticky top-8">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>{currentPlan.name} Plan</span>
                      {currentPlan.popular && (
                        <Badge className="bg-primary text-primary-foreground">
                          <Crown className="w-3 h-3 mr-1" />
                          Popular
                        </Badge>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center mb-6">
                      <div className="text-3xl font-bold text-primary mb-2">
                        {currentPlan.price}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {currentPlan.period}
                      </div>
                      {currentPlan.trialDays > 0 && (
                        <div className="mt-2 text-sm font-medium text-green-600">
                          {currentPlan.trialDays} days free trial
                        </div>
                      )}
                    </div>

                    <div className="space-y-3 mb-6">
                      {currentPlan.features.map((feature, index) => (
                        <div key={index} className="flex items-start">
                          <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 mr-3 flex-shrink-0" />
                          <span className="text-sm text-foreground">{feature}</span>
                        </div>
                      ))}
                    </div>

                    <div className="bg-muted/50 rounded-lg p-4 mb-6">
                      <h4 className="font-semibold text-foreground mb-3">What you get immediately:</h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center">
                          <Zap className="w-4 h-4 text-primary mr-2" />
                          <span>Instant account provisioning</span>
                        </div>
                        <div className="flex items-center">
                          <Shield className="w-4 h-4 text-primary mr-2" />
                          <span>Test environment with sample data</span>
                        </div>
                        <div className="flex items-center">
                          <Users className="w-4 h-4 text-primary mr-2" />
                          <span>Onboarding assistance</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-xs text-muted-foreground text-center">
                      {currentPlan.trialDays > 0 ? (
                        <>
                          No credit card required for trial.<br/>
                          Cancel anytime during trial period.
                        </>
                      ) : (
                        <>
                          Free forever for up to 100 customers.<br/>
                          Upgrade anytime as you grow.
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}