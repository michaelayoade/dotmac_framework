'use client'

import { useState } from 'react'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
// Using simple HTML elements to avoid missing component dependencies
import { 
  ArrowRight, 
  CheckCircle,
  Phone,
  Mail,
  Calendar,
  Users,
  Building,
  Crown,
  Shield,
  Zap,
  Clock,
  AlertCircle,
  Loader2
} from 'lucide-react'

interface ContactForm {
  companyName: string
  firstName: string
  lastName: string
  email: string
  phone: string
  jobTitle: string
  customerCount: string
  currentSolution: string
  timeframe: string
  requirements: string
  budget: string
  preferredContact: string
}

const enterpriseFeatures = [
  'Unlimited customers and users',
  'White-label solution with your branding',
  'Dedicated customer success manager',
  'Custom integrations and development',
  'Advanced security and compliance',
  'Priority support with SLA guarantees',
  'Professional implementation services',
  'Team training and certification'
]

const customerCounts = [
  '1,000-5,000',
  '5,001-10,000', 
  '10,001-25,000',
  '25,001-50,000',
  '50,000+'
]

const timeframes = [
  'Immediate (within 30 days)',
  '1-3 months',
  '3-6 months', 
  '6-12 months',
  'Exploring options'
]

const budgetRanges = [
  'Under $10K annually',
  '$10K-$50K annually',
  '$50K-$100K annually', 
  '$100K-$250K annually',
  '$250K+ annually',
  'Not sure yet'
]

export default function ContactSalesPage() {
  const [formData, setFormData] = useState<ContactForm>({
    companyName: '',
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    jobTitle: '',
    customerCount: '',
    currentSolution: '',
    timeframe: '',
    requirements: '',
    budget: '',
    preferredContact: 'email'
  })
  
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const response = await fetch('/api/contact-sales', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      if (!response.ok) {
        throw new Error('Failed to submit request')
      }

      setSuccess(true)
    } catch (error) {
      setError('Failed to submit request. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

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
                Thank you for your interest!
              </h1>
              
              <p className="text-lg text-muted-foreground mb-8">
                Our enterprise sales team will contact you within 2 business hours to discuss 
                your requirements and schedule a personalized demo.
              </p>
              
              <div className="bg-muted/50 rounded-xl p-6 mb-8">
                <h3 className="font-semibold text-foreground mb-4">What happens next:</h3>
                <div className="space-y-3 text-left">
                  <div className="flex items-center">
                    <Clock className="w-5 h-5 text-blue-600 mr-3" />
                    <span className="text-sm">Sales engineer review (within 2 hours)</span>
                  </div>
                  <div className="flex items-center">
                    <Phone className="w-5 h-5 text-blue-600 mr-3" />
                    <span className="text-sm">Initial consultation call scheduled</span>
                  </div>
                  <div className="flex items-center">
                    <Calendar className="w-5 h-5 text-blue-600 mr-3" />
                    <span className="text-sm">Custom demo environment prepared</span>
                  </div>
                  <div className="flex items-center">
                    <Crown className="w-5 h-5 text-blue-600 mr-3" />
                    <span className="text-sm">Enterprise proposal and pricing delivered</span>
                  </div>
                </div>
              </div>
              
              <Button asChild>
                <a href="/">Return to Homepage</a>
              </Button>
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
          {/* Header */}
          <div className="text-center mb-12">
            <Badge variant="secondary" className="mb-4">
              <Crown className="w-4 h-4 mr-2" />
              Enterprise Sales
            </Badge>
            <h1 className="text-3xl font-bold text-foreground mb-4">
              Let's discuss your <span className="text-gradient">enterprise needs</span>
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Get a custom solution designed for your ISP's specific requirements. 
              Our enterprise team will work with you to create the perfect platform configuration.
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-12 max-w-6xl mx-auto">
            {/* Contact Form */}
            <div>
              <Card>
                <CardHeader>
                  <CardTitle>Tell us about your requirements</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-6">
                    {error && (
                      <div className="flex items-center p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                        <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
                        <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
                      </div>
                    )}

                    {/* Company Info */}
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
                        />
                      </div>
                    </div>

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
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
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
                        />
                      </div>
                    </div>

                    <div>
                      <label htmlFor="jobTitle" className="block text-sm font-medium text-foreground mb-2">
                        Job Title
                      </label>
                      <input
                        type="text"
                        id="jobTitle"
                        name="jobTitle"
                        value={formData.jobTitle}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                        placeholder="CTO, VP of Operations, etc."
                      />
                    </div>

                    {/* Business Details */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label htmlFor="customerCount" className="block text-sm font-medium text-foreground mb-2">
                          Current Customers
                        </label>
                        <select
                          id="customerCount"
                          name="customerCount"
                          value={formData.customerCount}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                        >
                          <option value="">Select range</option>
                          {customerCounts.map(range => (
                            <option key={range} value={range}>{range}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label htmlFor="timeframe" className="block text-sm font-medium text-foreground mb-2">
                          Implementation Timeframe
                        </label>
                        <select
                          id="timeframe"
                          name="timeframe"
                          value={formData.timeframe}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                        >
                          <option value="">Select timeframe</option>
                          {timeframes.map(time => (
                            <option key={time} value={time}>{time}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div>
                      <label htmlFor="currentSolution" className="block text-sm font-medium text-foreground mb-2">
                        Current ISP Management Solution
                      </label>
                      <input
                        type="text"
                        id="currentSolution"
                        name="currentSolution"
                        value={formData.currentSolution}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                        placeholder="Currently using..., or Built in-house, or No current solution"
                      />
                    </div>

                    <div>
                      <label htmlFor="budget" className="block text-sm font-medium text-foreground mb-2">
                        Annual Budget Range
                      </label>
                      <select
                        id="budget"
                        name="budget"
                        value={formData.budget}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                      >
                        <option value="">Select budget range</option>
                        {budgetRanges.map(budget => (
                          <option key={budget} value={budget}>{budget}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label htmlFor="requirements" className="block text-sm font-medium text-foreground mb-2">
                        Specific Requirements or Questions
                      </label>
                      <textarea
                        id="requirements"
                        name="requirements"
                        rows={4}
                        value={formData.requirements}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                        placeholder="Tell us about your specific needs, integration requirements, compliance needs, etc."
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-foreground mb-3">
                        Preferred Contact Method
                      </label>
                      <div className="flex space-x-4">
                        <label className="flex items-center">
                          <input
                            type="radio"
                            name="preferredContact"
                            value="email"
                            checked={formData.preferredContact === 'email'}
                            onChange={handleInputChange}
                            className="mr-2"
                          />
                          Email
                        </label>
                        <label className="flex items-center">
                          <input
                            type="radio"
                            name="preferredContact"
                            value="phone"
                            checked={formData.preferredContact === 'phone'}
                            onChange={handleInputChange}
                            className="mr-2"
                          />
                          Phone Call
                        </label>
                        <label className="flex items-center">
                          <input
                            type="radio"
                            name="preferredContact"
                            value="video"
                            checked={formData.preferredContact === 'video'}
                            onChange={handleInputChange}
                            className="mr-2"
                          />
                          Video Call
                        </label>
                      </div>
                    </div>

                    <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
                      {isLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Submitting...
                        </>
                      ) : (
                        <>
                          Contact Enterprise Sales
                          <ArrowRight className="w-4 w-4 ml-2" />
                        </>
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </div>

            {/* Enterprise Benefits */}
            <div>
              <div className="space-y-8">
                {/* Enterprise Plan Features */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center">
                      <Crown className="w-6 h-6 text-primary mr-3" />
                      Enterprise Plan Includes
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {enterpriseFeatures.map((feature, index) => (
                        <div key={index} className="flex items-start">
                          <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 mr-3 flex-shrink-0" />
                          <span className="text-sm text-foreground">{feature}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Why Enterprise */}
                <Card>
                  <CardHeader>
                    <CardTitle>Why Choose Enterprise?</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-start">
                        <Shield className="w-6 h-6 text-blue-600 mt-1 mr-3" />
                        <div>
                          <h4 className="font-semibold text-foreground mb-1">Enhanced Security</h4>
                          <p className="text-sm text-muted-foreground">
                            SOC 2 Type II certified with custom security controls and compliance support.
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-start">
                        <Users className="w-6 h-6 text-green-600 mt-1 mr-3" />
                        <div>
                          <h4 className="font-semibold text-foreground mb-1">Dedicated Support</h4>
                          <p className="text-sm text-muted-foreground">
                            Named customer success manager and priority technical support with SLA guarantees.
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-start">
                        <Zap className="w-6 h-6 text-purple-600 mt-1 mr-3" />
                        <div>
                          <h4 className="font-semibold text-foreground mb-1">Custom Development</h4>
                          <p className="text-sm text-muted-foreground">
                            Bespoke features and integrations tailored specifically to your business needs.
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Contact Options */}
                <Card>
                  <CardHeader>
                    <CardTitle>Need Help Now?</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center">
                        <Phone className="w-5 h-5 text-primary mr-3" />
                        <div>
                          <div className="font-semibold">Call Enterprise Sales</div>
                          <div className="text-sm text-muted-foreground">+1 (555) 123-ENTER</div>
                        </div>
                      </div>
                      <div className="flex items-center">
                        <Mail className="w-5 h-5 text-primary mr-3" />
                        <div>
                          <div className="font-semibold">Email Enterprise Team</div>
                          <div className="text-sm text-muted-foreground">enterprise@dotmac.platform</div>
                        </div>
                      </div>
                      <div className="flex items-center">
                        <Calendar className="w-5 h-5 text-primary mr-3" />
                        <div>
                          <div className="font-semibold">Schedule Direct</div>
                          <div className="text-sm text-muted-foreground">Book a call on our calendar</div>
                        </div>
                      </div>
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